import logging
import unittest

from dockerfile_parse import DockerfileParser

from model import handle_error
from optimize import stage_optimizer
from optimize.optimization_strategy import *


class TestOptimizer(unittest.TestCase):

    def setUp(self):
        self.parser = DockerfileParser('tmp')

    def _lines_wrapper(self, lines: list) -> list:
        self.parser.lines = [line + '\n' for line in lines]
        instructions = self.parser.structure
        self.parser = DockerfileParser('tmp')  # Clear
        return instructions

    def test_wrong_dockerfile(self):
        try:
            lines = [
                'RUN --mount=type=cache,target useradd -d /home/panda panda && usermod -d /home/root root'
            ]
            strategy = AddCacheStrategy(0, ['/root'])
            print(stage_optimizer.StageOptimizer(self._lines_wrapper(lines)).optimize([strategy]))
        except handle_error.HandleError as e:
            print('You will see this')
            return


if __name__ == '__main__':
    unittest.main()
