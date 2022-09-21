"""
Copyright 2022 PandaAwAke

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


import getopt
import logging
import os

from dockerfile_parse import DockerfileParser

from model import handle_error
from model.stats import stats
from pipeline.dockerfile_writer import DockerfileWriter
from pipeline.optimize.global_optimizer import GlobalOptimizer
from pipeline.optimize.stage_optimizer import StageOptimizer
from pipeline.stage_simulator import StageSimulator
from pipeline.stage_splitter import StageSplitter


def _print_usage():
    usage = """\
Usage: python src/main.py [OPTIONS] INPUT
If INPUT is a directory, all files (including subdirectories) in it will be optimized.

Options:
  -h            Display this help message and exit
  -o OUTPUT     Optimized output dockerfile path, default to INPUT + SUFFIX
                (SUFFIX is ".optimized" by default, so this will be "INPUT.optimized" by default)
                If INPUT is a directory, then OUTPUT should be a directory too
  -s SUFFIX     Set the prefix of the output file, default to ".optimized"
                If INPUT and OUTPUT both are directories, then SUFFIX will be ignored
  -S            Show the statistics of optimizations
  -f FAIL_FILE  Output all dockerfiles that are failed to optimize into FAIL_FILE
                FAIL_FILE is './DPMO_failures.txt' by default
"""
    print(usage)


class Engine(object):
    """
    The engine (pipeline controller) of this tool.
    When encountered a HandleError (model.handle_error), it'll give up the optimization and just
    copy the input file to the output path.

    The pipeline of this tool can be described as follows:
    1.  Stage Splitter (pipeline.stage_splitter). It splits the dockerfile into stages,
        each of which starts with a "FROM" instruction.
    2.  Stage Simulator (pipeline.stage_simulator). It takes a stage, simulates the instructions
        inside it, and maintains a GlobalStatus (model.global_status) during the simulation.
        -   Every stage from Step 1 will be simulated separately. Stages won't interfere with
            each other.
        -   RUN instructions will be passed to RunHandler.
    3.  Run Handler (pipeline.run_handler). It takes a RUN instruction from Step 2, and parses
        the commands inside the instruction. Then it'll try to handle package-manager-related
        and global-status-related commands.
        -   Note that a RUN instruction can consist of multiple commands, such as
            "RUN apt-get update && apt-get install gcc".
        -   All package-manager-related commands will be passed to PMHandler.
    4.  PM Handler (pipeline.pm_handler), PM refers to Package Manager. PMHandler maintains
        a PMStatus for every PM. It takes pm-related commands in Step 3 and try to handle them.
        When it realized that this instruction can be optimized, it'll try to generate an
        OptimizationStrategy (pipeline.optimize.optimization_strategy).
    5.  Stage Optimizer (pipeline.optimize.stage_optimizer). It takes the stage, then tries to
        apply all optimization strategies in Step 4.
    6.  Global Optimizer (pipeline.optimize.global_optimizer). It takes all stages, and makes some
        global changes to the whole dockerfile.
    """

    class EngineSetting(object):
        """
        The settings of the engine.
        """

        def __init__(self):
            self.input_file = None
            self.output_file = None
            self.suffix = '.optimized'
            self.show_stats = False
            self.fail_file = './DPMO_failures.txt'
            self.fail_fileobj = None

    def __init__(self, argv):
        logging.basicConfig(
            format='[%(asctime)s %(levelname)s %(name)s]: %(message)s',
            level=logging.INFO
        )

        self.setting = Engine.EngineSetting()
        self._handle_argv(argv)
        try:
            self.setting.fail_fileobj = open(file=self.setting.fail_file, mode='w')
        except Exception as e:  # Including: IOError
            logging.error(e)
            exit(-1)

    def _handle_argv(self, argv):
        """
        Parse the command-line arguments, and then set the engine settings.
        :param argv: command-line arguments (sys.argv[1:])
        :return: None
        """
        try:
            opts, args = getopt.getopt(argv, 'ho:s:Sf:e')
        except getopt.GetoptError as e:
            logging.error('Invalid option: "{0}"'.format(e.opt))
            exit(-1)
        if len(opts) > 0 and opts[0][0] == '-h':
            _print_usage()
            exit(0)
        if len(args) == 0:
            logging.error('Input path is empty!')
            exit(-1)

        self.setting = Engine.EngineSetting()
        self.setting.input_file = args[0]

        for option, value in opts:
            if option == '-o':
                self.setting.output_file = value
            elif option == '-s':
                self.setting.suffix = value
            elif option == '-S':
                self.setting.show_stats = True
            elif option == '-f':
                self.setting.fail_file = value

    def run(self):
        """
        Process input file(s). The actual execution is in _run_one_file().
        :return: None
        """
        if os.path.isdir(self.setting.input_file):
            if self.setting.output_file is not None:
                if os.path.exists(self.setting.output_file) and not os.path.isdir(self.setting.output_file):
                    logging.error("INPUT is a directory, but OUTPUT isn't!")
                    exit(-1)
                elif not os.path.exists(self.setting.output_file):
                    os.mkdir(self.setting.output_file)
            self._optimize_directory()
        else:
            if self.setting.output_file is not None:
                self._run_one_file(self.setting.input_file, self.setting.output_file)
            else:
                self._run_one_file(self.setting.input_file, self.setting.input_file + self.setting.suffix)

    def _run_one_file(self, input_file: str, output_file: str):
        """
        Process one dockerfile, and execute the pipeline.
        :param input_file: the path of the dockerfile to be optimized.
        :param output_file: the path of the result to be saved.
        :return: None
        """
        try:
            f_in = open(file=input_file, mode='rb')
            f_out = open(file=output_file, mode='wb')

            # TODO: Add build-args support
            dockerfile_in = DockerfileParser(fileobj=f_in)
            dockerfile_out = DockerfileParser(fileobj=f_out)
        except Exception as e:  # Including: IOError
            logging.error(e)
            return

        try:
            splitter = StageSplitter(dockerfile=dockerfile_in)
            stages = splitter.get_stages()  # list of (instructions, contexts)
            if len(stages) == 0:
                logging.error('No stage is found in "{0}"! Is it correct?'.format(input_file))
                return

            if len(stages[0][0]) == 0:
                logging.info('Encountered an empty file: {0}'.format(input_file))
                return

            global_optimizer = GlobalOptimizer()
            if not global_optimizer.optimizable(stages):
                logging.error('"{0}" uses a non-official frontend, I cannot handle this.'.format(input_file))
                return

            logging.info('Optimizing {0} ...'.format(input_file))

            new_stages_lines = []
            total_strategies = 0
            for stage in stages:  # stage is (instructions, contexts)
                _simulator = StageSimulator(stage)
                _simulator.simulate()
                _optimizer = StageOptimizer(stage)
                strategies = _simulator.get_optimization_strategies()
                total_strategies += len(strategies)
                new_stage_lines = _optimizer.optimize(strategies)
                new_stages_lines.append(new_stage_lines)

            if total_strategies > 0:
                global_optimizer.optimize(stages, new_stages_lines)
                writer = DockerfileWriter(dockerfile_out)
                writer.write(new_stages_lines)
                logging.info('Successfully optimized {0} to {1}.'.format(input_file, output_file))
            else:
                # just copy output from input
                f_out.write(f_in.read())
                logging.info('{0} has nothing to optimize.'.format(input_file))

        except handle_error.HandleError as e:  # Failed to optimize this dockerfile
            # just copy output from input
            f_out.write(f_in.read())
            f_in.close()
            f_out.close()
            logging.info(
                'Failed to optimize {0}. The input file is copied.'.format(input_file, output_file))
            self.setting.fail_fileobj.write(input_file + '\n')
            stats.clear_one_file()
            return

        f_in.close()
        f_out.close()

        if self.setting.show_stats:
            logging.info(stats.one_file_str())

    def _optimize_directory(self):
        """
        Process the dockerfiles inside the input directory.
        The actual execution is in _run_one_file().
        :return:
        """
        input_dir = self.setting.input_file
        output_dir = self.setting.output_file
        for current_dir, dirs, files in os.walk(input_dir):
            for f in files:
                input_file = os.path.join(current_dir, f)
                if output_dir is None:
                    output_file = input_file + self.setting.suffix
                else:
                    output_file = os.path.join(output_dir,
                                               os.path.relpath(input_file, input_dir))
                self._run_one_file(input_file=input_file, output_file=output_file)
            if output_dir is not None:
                for d in dirs:
                    input_sub_dir = os.path.join(current_dir, d)
                    output_sub_dir = os.path.join(output_dir,
                                                  os.path.relpath(input_sub_dir, input_dir))
                    if not os.path.exists(output_sub_dir):
                        os.mkdir(output_sub_dir)
        if self.setting.show_stats:
            logging.info(stats.total_str())
