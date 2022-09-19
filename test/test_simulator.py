import unittest

from dockerfile_parse import DockerfileParser

from model.global_status import GlobalStatus
from pipeline import stage_simulator


class TestSimulator(unittest.TestCase):

    def setUp(self):
        self.parser = DockerfileParser('tmp')

    def _lines_wrapper(self, lines: list) -> list:
        self.parser.lines = [line + '\n' for line in lines]
        instructions = self.parser.structure
        self.parser = DockerfileParser('tmp')  # Clear
        return instructions

    def test_handle_user_workdir(self):
        lines = [
            'RUN useradd -d /home/panda panda && usermod -d /home/root root',
            'USER panda1',
            'WORKDIR home',
            'WORKDIR panda',
            'USER panda'
        ]
        s = stage_simulator.StageSimulator(self._lines_wrapper(lines))
        s.simulate(0, 1)
        self.assertEqual(s.global_status, GlobalStatus(
            work_dir='/', user='root', user_dirs={'panda': '/home/panda/', 'root': '/home/root/'}
        ))
        s.simulate(1, 2)
        self.assertEqual(s.global_status, GlobalStatus(
            work_dir='/', user='panda1', user_dirs={'panda': '/home/panda/', 'root': '/home/root/'}
        ))
        s.simulate(2, 4)
        self.assertEqual(s.global_status, GlobalStatus(
            work_dir='/home/panda/', user='panda1', user_dirs={'panda': '/home/panda/', 'root': '/home/root/'}
        ))
        s.simulate(4, 5)
        self.assertEqual(s.global_status, GlobalStatus(
            work_dir='/home/panda/', user='panda', user_dirs={'panda': '/home/panda/', 'root': '/home/root/'}
        ))

    def test_shell(self):
        pass

    # def test_pm_


if __name__ == '__main__':
    unittest.main()
