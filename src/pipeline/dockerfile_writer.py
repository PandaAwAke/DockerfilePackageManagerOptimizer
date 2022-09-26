from functools import reduce

import dockerfile_parse


class DockerfileWriter(object):
    """
    The writer for optimized dockerfile from GlobalOptimizer.
    """

    def __init__(self, dockerfile: dockerfile_parse.DockerfileParser = None):
        """
        Initialize the DockerfileWriter.

        :param dockerfile: the dockerfile object of the output dockerfile.
        """
        self.dockerfile = dockerfile

    def write(self, stages_lines: list):
        """
        Write the stage_lines into the output dockerfile.

        :param stages_lines:
        :return: None
        """
        self.dockerfile.lines = reduce(lambda x, y: x + y, stages_lines)
