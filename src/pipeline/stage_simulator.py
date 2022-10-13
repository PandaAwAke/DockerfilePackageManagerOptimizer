from model.global_status import GlobalStatus
from pipeline.run_handler import RunHandler


class StageSimulator(object):
    """
    Take a stage, simulates the instructions inside it, and maintain the
    GlobalStatus (model.global_status) during the simulation.

    -   RUN instructions will be passed to RunHandler.
    """

    def __init__(self, stage):
        """
        Initialize the stage simulator.

        :param stage: the stage to simulate.
        """
        # a stage is (instructions, contexts)
        self.instructions, self.contexts = stage
        self.global_status = GlobalStatus()
        self.optimization_strategies = []
        self.run_handler = RunHandler(self.global_status, self.optimization_strategies)

    def simulate(self, start_instruction_index=0, end_instruction_index=-1):
        """
        Simulate the instructions of the stage.

        -   USER and WORKDIR instructions will update the global_status.
        -   RUN instructions will be passed to RunHandler.

        :param start_instruction_index:
        :param end_instruction_index:
        :return:
        """
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
                user_name = value
                if self.global_status.user_dirs.get(user_name) is None:
                    if user_name != 'root':
                        user_home = '/home/' + user_name + '/'
                    else:
                        user_home = '/root/'
                    self.global_status.user_dirs[user_name] = user_home
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
        """
        Get the optimization strategies from PMHandler.

        :return: the optimization strategies.
        """
        return self.optimization_strategies
