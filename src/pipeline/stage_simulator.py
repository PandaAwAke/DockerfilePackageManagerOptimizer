from model.global_status import GlobalStatus
from pipeline.run_handler import RunHandler


class StageSimulator(object):
    def __init__(self, stage):
        # stage is (instructions, contexts)
        self.instructions, self.contexts = stage
        self.global_status = GlobalStatus()
        self.run_handler = RunHandler(self.global_status)

    def simulate(self, start_instruction_index=0, end_instruction_index=-1):
        if end_instruction_index < 0 or end_instruction_index > len(self.instructions):
            end_instruction_index = len(self.instructions)
        assert 0 <= start_instruction_index <= end_instruction_index
        for instruction_index in range(start_instruction_index, end_instruction_index):
            instruction = self.instructions[instruction_index]
            context = self.contexts[instruction_index]
            i_type: str = instruction['instruction']
            value: str = instruction['value']
            # Other types of instructions are ignored
            if i_type == 'USER':
                self.global_status.user = value
            elif i_type == 'WORKDIR':
                if not value.endswith('/'):
                    value += '/'
                if value.startswith('/'):   # Absolute dir
                    self.global_status.work_dir = value
                else:                       # Relative dir
                    self.global_status.work_dir += value
            elif i_type == 'RUN':
                self.run_handler.handle(value, context, instruction_index)
            # TODO: Consider more instructions
            # elif i_type == "VOLUME":
            #     ...
            # elif i_type == "ADD" or i_type == "COPY":
            #     ...
            # elif i_type == "ARG" or i_type == "ENV":
            #     ...

    def get_optimization_strategies(self):
        return self.run_handler.pm_handler.optimization_strategies
