
class OptimizationStrategy:
    def __init__(self, instruction_index: int):
        self.instruction_index = instruction_index


class AddCacheStrategy(OptimizationStrategy):
    def __init__(self, instruction_index: int, cache_dirs: list):
        super().__init__(instruction_index=instruction_index)
        self.cache_dirs = cache_dirs


class InsertBeforeStrategy(OptimizationStrategy):
    def __init__(self, instruction_index: int, commands_insert: list):
        super().__init__(instruction_index=instruction_index)
        self.commands_insert = commands_insert
