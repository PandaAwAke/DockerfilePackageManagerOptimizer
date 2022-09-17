import logging
import getopt

from stage_splitter import StageSplitter
from simulator import Simulator
from optimize.stage_optimizer import StageOptimizer
from optimize.global_optimizer import GlobalOptimizer
from dockerfile_writer import DockerfileWriter
from stats import stats

from dockerfile_parse import DockerfileParser


def _print_usage():
    usage = \
        """Usage: doco [OPTIONS] INPUT

Options:
-h              display this help message and exit
-o OUTPUT       optimized output dockerfile path, default to "INPUT.optimized"
"""
    print(usage)


class Engine(object):
    class EngineSetting(object):
        def __init__(self, input_file):
            self.input_file = input_file
            self.output_file = input_file + '.optimized'

    def __init__(self, argv):
        self.setting: Engine.EngineSetting
        self._handle_argv(argv)

    def _handle_argv(self, argv):
        try:
            opts, args = getopt.getopt(argv, 'ho:')
        except getopt.GetoptError as e:
            logging.error('Invalid option: {0}'.format(e.opt))
            exit(-1)
        if len(opts) == 1 and opts[0][0] == '-h':
            _print_usage()
            exit(0)
        if len(args) == 0:
            logging.error('Input path is empty!')
            exit(-1)

        self.setting = Engine.EngineSetting(args[0])

        for option, value in opts:
            if option == '-o':
                self.setting.output_file = value

    def run(self):
        try:
            f_in = open(file=self.setting.input_file, mode='rb')
            f_out = open(file=self.setting.output_file, mode='wb')

            # TODO: Add build-args support
            dockerfile_in = DockerfileParser(fileobj=f_in)
            dockerfile_out = DockerfileParser(fileobj=f_out)
        except Exception as e:  # Including: IOError
            logging.error(e)
            exit(-1)

        splitter = StageSplitter(dockerfile=dockerfile_in)
        stages = splitter.get_stages()
        if len(stages) == 0:
            logging.error('No stage is found in the input dockerfile! Is it correct?')
            exit(-1)

        global_optimizer = GlobalOptimizer()
        if not global_optimizer.optimizable(stages):
            logging.error('This dockerfile uses a non-official frontend, I cannot handle this.')
            exit(-1)

        new_stages_lines = []
        for stage in stages:
            _simulator = Simulator(stage)
            _simulator.simulate()
            _optimizer = StageOptimizer(stage)
            new_stage_lines = _optimizer.optimize(_simulator.get_optimization_strategies())
            new_stages_lines.append(new_stage_lines)

        global_optimizer.optimize(stages, new_stages_lines)

        writer = DockerfileWriter(dockerfile_out)
        writer.write(new_stages_lines)

        f_in.close()
        f_out.close()

        logging.info('Successfully optimized {0} into {1}.'.format(self.setting.input_file, self.setting.output_file))
