import logging

import dockerfile_parse

from model import handle_error


class StageSplitter(object):
    def __init__(self, dockerfile: dockerfile_parse.DockerfileParser = None):
        if dockerfile is None:
            logging.error('dockerfile=None is provided to stage splitter!')
            raise handle_error.HandleError()
        self.dockerfile = dockerfile

    def get_stages(self):
        if not self.dockerfile.is_multistage:
            return [(self.dockerfile.structure, self.dockerfile.context_structure)]
        else:
            instructions = []
            contexts = []
            stages = []
            first_FROM = True
            for i in range(len(self.dockerfile.structure)):
                instruction = self.dockerfile.structure[i]
                context = self.dockerfile.context_structure[i]
                if instruction['instruction'] == 'FROM':
                    if first_FROM:
                        first_FROM = False
                    else:
                        stages.append((instructions, contexts))
                        instructions = []
                        contexts = []
                instructions.append(instruction)
                contexts.append(context)
            if len(instructions) > 0:
                stages.append((instructions, contexts))
            return stages

