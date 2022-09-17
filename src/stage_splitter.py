import logging

import dockerfile_parse

import handle_error


class StageSplitter(object):
    def __init__(self, dockerfile: dockerfile_parse.DockerfileParser = None):
        if dockerfile is None:
            logging.error('dockerfile=None is provided to stage splitter!')
            raise handle_error.HandleError()
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

