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


import logging
import os
import sys

from dockerfile_parse import DockerfileParser

from config.engine_config import engine_settings
from config.optimization_config import load_optimization_settings
from model import handle_error
from model.optimization_strategy import AddCacheStrategy
from model.stats import stats
from pipeline.dockerfile_writer import DockerfileWriter
from pipeline.global_optimizer import GlobalOptimizer
from pipeline.stage_optimizer import StageOptimizer
from pipeline.stage_simulator import StageSimulator
from pipeline.stage_splitter import StageSplitter


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

    def __init__(self):
        load_optimization_settings()

    def run(self):
        """
        Process input file(s). The actual execution is in _run_one_file().

        :return: None
        """
        if os.path.isdir(engine_settings.input_file):   # Input is a directory
            if engine_settings.output_file is not None:
                if os.path.exists(engine_settings.output_file) and \
                        not os.path.isdir(engine_settings.output_file):
                    logging.error("INPUT is a directory, but OUTPUT isn't!")
                    sys.exit(-1)
                self._create_output_directory(engine_settings.output_file)
            self._optimize_directory()
        else:       # Input is a file
            if engine_settings.output_file is not None:
                if os.path.isdir(engine_settings.output_file):
                    self._run_one_file(engine_settings.input_file,
                                       os.path.join(
                                           engine_settings.output_file,
                                           os.path.basename(engine_settings.input_file)))
                else:
                    self._create_output_directory(os.path.dirname(engine_settings.output_file))
                    self._run_one_file(engine_settings.input_file, engine_settings.output_file)
            else:
                self._run_one_file(engine_settings.input_file, engine_settings.input_file + engine_settings.suffix)

        logging.warning(stats.total_str())
        stats.optimization_dict_write_stat_file()

    @staticmethod
    def _run_one_file(input_file: str, output_file: str):
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

        valid_dockerfile = True

        try:
            logging.info("Optimizing - {0}".format(input_file))

            splitter = StageSplitter(dockerfile=dockerfile_in)
            stages = splitter.get_stages()  # list of (instructions, contexts)
            if len(stages) == 0:
                logging.error("Unchanged - {0} - No stage was found! Is it correct?".format(input_file))
                valid_dockerfile = False

            if len(stages[0][0]) == 0:
                logging.info("Unchanged - {0} - Encountered an empty file.".format(input_file))
                valid_dockerfile = False

            global_optimizer = GlobalOptimizer()
            if valid_dockerfile:
                if not global_optimizer.optimizable(stages):
                    logging.error("Unchanged - {0} - A non-official frontend was used, I cannot handle this."
                                  .format(input_file))
                    valid_dockerfile = False

            if valid_dockerfile:
                new_stages_lines = []
                something_can_be_optimized = False
                for stage in stages:  # stage is (instructions, contexts)
                    _simulator = StageSimulator(stage)
                    _simulator.simulate()
                    _optimizer = StageOptimizer(stage, dockerfile_in.lines)
                    strategies = _simulator.get_optimization_strategies()

                    add_cache_strategies = len([s for s in strategies if isinstance(s, AddCacheStrategy)])
                    if add_cache_strategies > 0:
                        something_can_be_optimized = True
                        new_stage_lines = _optimizer.optimize(strategies)
                    else:
                        new_stage_lines = _optimizer.optimize([])

                    if stage is not stages[-1]:
                        new_stage_lines.append('\n\n')

                    new_stages_lines.append(new_stage_lines)

                if something_can_be_optimized:
                    global_optimizer.optimize(stages, new_stages_lines)
                    writer = DockerfileWriter(dockerfile_out)
                    writer.write(new_stages_lines)
                    stats.successful_one_file()
                    logging.info("Successful - {0} - {1}".format(input_file, output_file))
                else:
                    # just copy output from input
                    stats.unchanged_one_file()
                    logging.info("Unchanged - {0} - Nothing can be optimized.".format(input_file))
                    f_out.write(f_in.read())
            else:
                stats.unchanged_one_file()

        except handle_error.HandleError as e:  # An error occurred when optimizing this dockerfile
            # just copy output from input
            f_out.write(f_in.read())

            stats.failed_one_file()
            logging.warning(
                "Unchanged - {0} - The input file is copied.".format(input_file, output_file))
            engine_settings.fail_fileobj.write(input_file + '\n')

        finally:
            f_in.close()
            f_out.close()

            if engine_settings.show_stats:
                logging.info(stats.one_file_str())

            stats.finished_one_file(input_file)

    def _optimize_directory(self):
        """
        Process the dockerfiles inside the input directory.
        The actual execution is in _run_one_file().

        :return: None
        """
        input_dir = engine_settings.input_file
        output_dir = engine_settings.output_file
        for current_dir, dirs, files in os.walk(input_dir):
            for f in files:
                input_file = os.path.join(current_dir, f)
                if output_dir is None:
                    output_file = input_file + engine_settings.suffix
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

    def _create_output_directory(self, output_dir):
        """
        Create directory output_dir recursively.
        :param output_dir: the directory path to create.
        :return: None
        """
        if os.path.exists(output_dir) or output_dir == '':
            return
        else:
            self._create_output_directory(os.path.dirname(output_dir))
            os.mkdir(output_dir)
