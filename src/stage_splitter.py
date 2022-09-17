import logging

import dockerfile_parse


class StageSplitter(object):
    def __init__(self, dockerfile: dockerfile_parse.DockerfileParser = None):
        if dockerfile is None:
            logging.error('Empty dockerfile is provided to stage splitter!')
            exit(-1)
        self.dockerfile = dockerfile

    def get_stages(self):
        if not self.dockerfile.is_multistage:
            return [self.dockerfile.structure]
        else:
            instructions = []
            stages = []
            for instruction in self.dockerfile.structure:
                if instruction['instruction'] == 'FROM':
                    stages.append(instructions)
                    instructions = []
                instructions.append(instruction)
            if len(instructions) > 0:
                stages.append(instructions)
            return stages

