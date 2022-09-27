import unittest

from dockerfile_parse import DockerfileParser

import config
from model import handle_error
from pipeline.stage_optimizer import StageOptimizer
from pipeline.stage_simulator import StageSimulator


class TestAll(unittest.TestCase):

    def setUp(self):
        self.parser = DockerfileParser('tmp')
        config.global_settings.pm_settings_path = '../resources/PMSettings.yaml'

    def _lines_wrapper(self, lines: list) -> tuple:
        self.parser.lines = [line + '\n' for line in lines]
        instructions, contexts = self.parser.structure, self.parser.context_structure
        self.parser = DockerfileParser('tmp')  # Clear
        return instructions, contexts

    def _execute_one_stage(self, lines: list):
        stage = self._lines_wrapper(lines)
        try:
            _simulator = StageSimulator(stage)
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

    def test_run_exec_form(self):
        lines = [
            'RUN --mount=type=cache,target=/var/lib/apt [ "apt-get", "update" ]',
            'RUN --mount=type=cache,target=/var/lib/apt go install && apt-get install'
        ]
        result = self._execute_one_stage(lines)
        print(result)
        self.assertEqual(result,
        [
         'RUN rm -f /etc/apt/apt.conf.d/docker-clean; echo \'Binary::apt::APT::Keep-Downloaded-Packages "true";\' > /etc/apt/apt.conf.d/keep-cache\n',
         'RUN --mount=type=cache,target=/var/cache/apt --mount=type=cache,target=/var/lib/apt [ "apt-get", "update" ]\n',
         'RUN --mount=type=cache,target=/root/.cache/go-build --mount=type=cache,target=/var/cache/apt --mount=type=cache,target=/var/lib/apt go install && apt-get install\n'
        ])

    def test_bash_exec_form(self):
        lines = [
            'RUN --mount=type=cache,target=/var/lib/apt [ "bash", "-c", "apt-get update" ]',
            'RUN --mount=type=cache,target=/var/lib/apt go install && apt-get install'
        ]
        result = self._execute_one_stage(lines)
        print(result)
        self.assertEqual(result,
        [
         'RUN rm -f /etc/apt/apt.conf.d/docker-clean; echo \'Binary::apt::APT::Keep-Downloaded-Packages "true";\' > /etc/apt/apt.conf.d/keep-cache\n',
         'RUN --mount=type=cache,target=/var/cache/apt --mount=type=cache,target=/var/lib/apt [ "bash", "-c", "apt-get update" ]\n',
         'RUN --mount=type=cache,target=/root/.cache/go-build --mount=type=cache,target=/var/cache/apt --mount=type=cache,target=/var/lib/apt go install && apt-get install\n'
        ])

    def test_env(self):
        lines = [
            'ENV dir=/var/lib/apt',
            'RUN apt update',
            'RUN --mount=type=cache,target=${dir} apt-get install'
        ]
        result = self._execute_one_stage(lines)
        self.assertEqual(result, [
            'ENV dir=/var/lib/apt\n',
            'RUN rm -f /etc/apt/apt.conf.d/docker-clean; echo \'Binary::apt::APT::Keep-Downloaded-Packages "true";\' '
            '> /etc/apt/apt.conf.d/keep-cache\n',
            'RUN --mount=type=cache,target=/var/lib/apt --mount=type=cache,target=/var/cache/apt apt update\n',
            'RUN --mount=type=cache,target=/var/cache/apt --mount=type=cache,target=${dir} apt-get install\n'
        ])


if __name__ == '__main__':
    unittest.main()
