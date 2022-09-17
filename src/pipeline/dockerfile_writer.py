from functools import reduce

import dockerfile_parse


class DockerfileWriter(object):

    def __init__(self, dockerfile: dockerfile_parse.DockerfileParser = None):
        self.dockerfile = dockerfile

    def write(self, stages_lines: list):
        self.dockerfile.lines = reduce(lambda x, y: x + y, stages_lines)
