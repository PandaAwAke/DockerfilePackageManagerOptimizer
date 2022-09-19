import getopt
import logging
import os

from dockerfile_parse import DockerfileParser

from model import handle_error
from model.stats import stats
from optimize.global_optimizer import GlobalOptimizer
from optimize.stage_optimizer import StageOptimizer
from pipeline.dockerfile_writer import DockerfileWriter
from pipeline.stage_simulator import StageSimulator
from pipeline.stage_splitter import StageSplitter


def _print_usage():
    usage = \
        """Usage: python src/main.py [OPTIONS] INPUT
If INPUT is a directory, all files (including subdirectories) in it will be optimized.

Options:
  -h            Display this help message and exit
  -o OUTPUT     Optimized output dockerfile path, default to INPUT + SUFFIX
                (SUFFIX is ".optimized" by default, so this will be "INPUT.optimized" by default)
                If INPUT is a directory, then OUTPUT should be a directory too
  -s SUFFIX     Set the prefix of the output file, default to ".optimized"
                If INPUT and OUTPUT both are directories, then SUFFIX will be ignored
  -S            Show the statistics of optimizations.
"""
    print(usage)


class Engine(object):
    class EngineSetting(object):
        def __init__(self, input_file):
            self.input_file = input_file
            self.output_file = None
            self.suffix = '.optimized'
            self.show_stats = False

    def __init__(self, argv):
        self.setting: Engine.EngineSetting
        self._handle_argv(argv)

    def _handle_argv(self, argv):
        try:
            opts, args = getopt.getopt(argv, 'ho:s:S')
        except getopt.GetoptError as e:
            logging.error('Invalid option: "{0}"'.format(e.opt))
            exit(-1)
        if len(opts) > 0 and opts[0][0] == '-h':
            _print_usage()
            exit(0)
        if len(args) == 0:
            logging.error('Input path is empty!')
            exit(-1)

        self.setting = Engine.EngineSetting(args[0])

        for option, value in opts:
            if option == '-o':
                self.setting.output_file = value
            elif option == '-s':
                self.setting.suffix = value
            elif option == '-S':
                self.setting.show_stats = True

    def run(self):
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

            new_stages_lines = []
            for stage in stages:    # stage is (instructions, contexts)
                _simulator = StageSimulator(stage)
                _simulator.simulate()
                _optimizer = StageOptimizer(stage)
                new_stage_lines = _optimizer.optimize(_simulator.get_optimization_strategies())
                new_stages_lines.append(new_stage_lines)

            global_optimizer.optimize(stages, new_stages_lines)

            writer = DockerfileWriter(dockerfile_out)
            writer.write(new_stages_lines)
        except handle_error.HandleError as e:   # Failed to optimize this dockerfile
            f_in.close()
            f_out.close()
            logging.info(
                'Failed to optimize {0}.'.format(input_file, output_file))
            stats.clear()
            return

        f_in.close()
        f_out.close()
        logging.info('Successfully optimized {0} to {1}.'.format(input_file, output_file))
        if self.setting.show_stats:
            logging.info(stats)

    def _optimize_directory(self):
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
            logging.info(stats.totalStr())
