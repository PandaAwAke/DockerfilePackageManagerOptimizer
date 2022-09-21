import logging

import dockerfile_parse

from model import handle_error


class StageSplitter(object):
    """
    Split the dockerfile into stages, each of which starts with a "FROM" instruction.
    """

    def __init__(self, dockerfile: dockerfile_parse.DockerfileParser = None):
        """
        Initialize the splitter.
        :param dockerfile: the DockerfileParser object of the input dockerfile.
        """
        if dockerfile is None:
            logging.error('dockerfile=None is provided to stage splitter!')
            raise handle_error.HandleError()
        self.dockerfile = dockerfile

    def get_stages(self):
        """
        Split the dockerfile into stages.
        :return: a list of stages. A stage is (instructions, contexts).
            -   instructions: a list of instructions, an instruction is a dict (from dockerfile_parse.parser):
                {"instruction": "FROM",       # always upper-case
                 "startline": 0,              # 0-based
                 "endline": 0,                # 0-based
                 "content": "From fedora\n",
                 "value": "fedora"},
            -   contexts: a list of contexts, a context is a dockerfile_parse.util.Context object. It describes
                the arguments/environment variables/labels values available to the instruction:
                context.args: dict with arguments valid for this line
                    (all variables defined to this line)
                context.envs: dict with variables valid for this line
                    (all variables defined to this line)
                context.labels: dict with labels valid for this line
                    (all labels defined to this line)
                context.line_args: dict with arguments defined on this line
                context.line_envs: dict with variables defined on this line
                context.line_labels: dict with labels defined on this line

            So the final structure of stages is:
            [(stage1_instructions, stage1_contexts), ..., (stagen_instructions, stagen_contexts)]
        """
        if not self.dockerfile.is_multistage:
            return [(self.dockerfile.structure, self.dockerfile.context_structure)]
        else:
            instructions = []
            contexts = []
            stages = []
            first_stage = True
            for i in range(len(self.dockerfile.structure)):
                instruction = self.dockerfile.structure[i]
                context = self.dockerfile.context_structure[i]
                if instruction['instruction'] == 'FROM':
                    if first_stage:
                        first_stage = False
                    else:
                        stages.append((instructions, contexts))
                        instructions = []
                        contexts = []
                instructions.append(instruction)
                contexts.append(context)
            if len(instructions) > 0:
                stages.append((instructions, contexts))
            return stages

