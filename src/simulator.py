from global_status import GlobalStatus
from run_handler import RunHandler


class Simulator(object):
    def __init__(self, instructions):
        self.instructions = instructions
        self.global_status = GlobalStatus()
        self.run_handler = RunHandler(self.global_status)

    def simulate(self):
        instruction_index = 0
        for instruction in self.instructions:
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
                self.run_handler.handle(value, instruction_index)
            # TODO: Consider more instructions
            # elif i_type == "VOLUME":
            #     ...
            # elif i_type == "ADD" or i_type == "COPY":
            #     ...
            # elif i_type == "ARG" or i_type == "ENV":
            #     ...
            instruction_index += 1

    def get_optimization_strategies(self):
        return self.run_handler.pm_handler.optimization_strategies
