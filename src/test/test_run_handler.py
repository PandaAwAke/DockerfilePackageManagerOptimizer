import unittest

import run_handler
import simulator


class TestRunHandler(unittest.TestCase):

    def setUp(self):
        self.rh = run_handler.RunHandler(simulator.GlobalStatus())

    def test_handle_user(self):
        self.rh.handle(' useradd -d /home/panda panda   &&   \n usermod -d /root root')
        self.assertEqual(self.rh.global_status.user_dirs,
                         {'panda': '/home/panda/', 'root': '/root/'})


if __name__ == '__main__':
    unittest.main()
