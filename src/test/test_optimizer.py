import unittest

import optimize.stage_optimizer


class TestOptimizer(unittest.TestCase):

    def setUp(self):
        self.op = optimize.stage_optimizer.StageOptimizer(None)

    def test_optimize_add_cache(self):
        self.op._optimize_add_cache(None, {
            'instruction': 'RUN',
            'value': '--mount=type=cache,target=/var/cache/apt --mount=type=cache,target=/var/lib/apt    apt-get '
                     'update &&     apt-get -y install wget nginx mongodb php5-fpm nginx git '
        }, None)


if __name__ == '__main__':
    unittest.main()
