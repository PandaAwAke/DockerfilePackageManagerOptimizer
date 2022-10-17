import unittest

from dockerfile_parse import DockerfileParser

from config import engine_config
from config.optimization_config import load_optimization_settings
from model import handle_error
from pipeline.stage_optimizer import StageOptimizer
from pipeline.stage_simulator import StageSimulator


class TestAll(unittest.TestCase):

    def setUp(self):
        self.parser = DockerfileParser('tmp')
        engine_config.global_settings.pm_settings_path = '../resources/settings.yaml'
        load_optimization_settings()

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
            _optimizer = StageOptimizer(stage, self.parser.lines)
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

    def test_anti_cache(self):
        lines = [
            'RUN rm -rf /var/lib/apt/lists/*',
            'RUN rm -rf /var/lib/apt/lists/* && apt-get update',
            'RUN echo 3 && rm -rf /var/lib/apt/lists/* || echo 5',
            'RUN echo 3 && \\\n rm -rf /var/lib/apt/lists/*  ',
            'RUN --mount=type=cache,target=/var/lib/apt rm -rf /var/lib/apt/lists/* && apt-get install || rm -rf /var/cache/apt/*'
        ]
        result = self._execute_one_stage(lines)
        self.assertEqual(result, [
            'RUN rm -f /etc/apt/apt.conf.d/docker-clean; echo \'Binary::apt::APT::Keep-Downloaded-Packages "true";\' > /etc/apt/apt.conf.d/keep-cache\n',
            'RUN --mount=type=cache,target=/var/lib/apt --mount=type=cache,target=/var/cache/apt  apt-get update\n',
            'RUN echo 3 && echo 5\n', 'RUN echo 3\n',
            'RUN --mount=type=cache,target=/var/cache/apt --mount=type=cache,target=/var/lib/apt  apt-get install\n'])

    def test_modify_cache_dir(self):
        lines = [
            'RUN npm install',
            'RUN npm config set prefix /root/npmcache',
            'RUN npm install',
            'RUN pip install pandas',
            'USER panda',
            'RUN pip install pandas',
            'RUN mkdir /root/.npm-global && npm config set prefix "/root/.npm-global"',
            'RUN npm install',
        ]
        result = self._execute_one_stage(lines)
        self.assertEqual(result, [
            'RUN --mount=type=cache,target=/root/.npm npm install\n',
            'RUN npm config set prefix /root/npmcache\n',
            'RUN --mount=type=cache,target=/root/npmcache npm install\n',
            'RUN --mount=type=cache,target=/root/.cache/pip pip install pandas\n', 'USER panda\n',
            'RUN --mount=type=cache,target=/home/panda/.cache/pip pip install pandas\n',
            'RUN mkdir /root/.npm-global && npm config set prefix "/root/.npm-global"\n',
            'RUN --mount=type=cache,target=/root/.npm-global npm install\n'
        ])


    def test_remove_anti_cache_options(self):
        lines = [
            'RUN pip --no-cache-dir install',
            'RUN pip --no-cache install',
            'RUN pip --no-cache-dir --no-cache install',
        ]
        result = self._execute_one_stage(lines)
        self.assertEqual(result, [
            'RUN --mount=type=cache,target=/root/.cache/pip pip install\n',
            'RUN --mount=type=cache,target=/root/.cache/pip pip install\n',
            'RUN --mount=type=cache,target=/root/.cache/pip pip install\n'
        ])




if __name__ == '__main__':
    unittest.main()
