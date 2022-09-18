import unittest

from dockerfile_parse import DockerfileParser

from model import handle_error
from optimize.stage_optimizer import StageOptimizer
from pipeline.simulator import Simulator


class TestAll(unittest.TestCase):

    def setUp(self):
        self.parser = DockerfileParser('tmp')

    def _lines_wrapper(self, lines: list) -> list:
        self.parser.lines = [line + '\n' for line in lines]
        instructions = self.parser.structure
        self.parser = DockerfileParser('tmp')  # Clear
        return instructions

    def _execute_one_stage(self, lines: list):
        stage = self._lines_wrapper(lines)
        try:
            _simulator = Simulator(stage)
            _simulator.simulate()
            _optimizer = StageOptimizer(stage)
            new_stage_lines = _optimizer.optimize(_simulator.get_optimization_strategies())
        except handle_error.HandleError as e:
            print('A handle error was raised')
            return ''
        return new_stage_lines

    def test_user_and_multiple_apt(self):
        lines = [
            'RUN apt update',
            'RUN --mount=type=cache,target=/var/lib/apt apt-get install'
        ]
        result = self._execute_one_stage(lines)
        self.assertEqual(result, [
            'RUN rm -f /etc/apt/apt.conf.d/docker-clean; echo \'Binary::apt::APT::Keep-Downloaded-Packages "true";\' '
            '> /etc/apt/apt.conf.d/keep-cache\n',
            'RUN --mount=type=cache,target=/var/lib/apt --mount=type=cache,target=/var/cache/apt apt update\n',
            'RUN --mount=type=cache,target=/var/cache/apt --mount=type=cache,target=/var/lib/apt apt-get install\n'
        ])



if __name__ == '__main__':
    unittest.main()
