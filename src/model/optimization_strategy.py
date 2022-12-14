"""
Copyright 2022 PandaAwAke

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


class OptimizationStrategy:
    """
    The base class for optimization strategy.
    """
    def __init__(self, instruction_index: int):
        """
        Initialize the basic optimization strategy.

        :param instruction_index: the index of the instruction.
        """
        self.instruction_index = instruction_index


class AddCacheStrategy(OptimizationStrategy):
    """
    The "Add-Cache" optimization strategy for an instruction.
    """

    def __init__(self, instruction_index: int, cache_dirs: list):
        """
        Initialize the strategy.

        :param instruction_index: the index of the instruction.
        :param cache_dirs: the cache directories need to be added inside "--mount=type=cache".
        """
        super().__init__(instruction_index=instruction_index)
        self.cache_dirs = cache_dirs


class InsertBeforeStrategy(OptimizationStrategy):
    """
    The "Insert-Command-Before" optimization strategy for an instruction.
    """

    def __init__(self, instruction_index: int, commands_insert: list):
        """
        Initialize the strategy.

        :param instruction_index: the index of the instruction.
        :param commands_insert: the commands need to be added before this instruction.
        """
        super().__init__(instruction_index=instruction_index)
        self.commands_insert = commands_insert


class RemoveCommandStrategy(OptimizationStrategy):
    """
    The "Remove-Command" optimization strategy for an instruction.
    """

    def __init__(self, instruction_index: int, remove_command_indices: list, remove_command_contents: list):
        """
        Initialize the strategy.

        :param instruction_index: the index of the instruction.
        :param remove_command_indices: the indices of commands need to be removed in this instruction.
        :param remove_command_contents: the contents inside the commands need to be removed.
                                Value inside it can be None or a list of strings.
                                if remove_command_contents[i] is None, remove the whole command i,
                                if remove_command_contents[i] is a list, remove them inside command i.
        """
        assert len(remove_command_indices) == len(remove_command_contents)
        super().__init__(instruction_index=instruction_index)
        self.remove_command_indices = remove_command_indices
        self.remove_command_contents = remove_command_contents


class RemoveOptionStrategy(OptimizationStrategy):
    """
    The "Remove-Option" optimization strategy for an instruction.
    """

    def __init__(self, instruction_index: int, command_index: int, remove_options: list):
        """
        Initialize the strategy.

        :param instruction_index: the index of the instruction.
        :param remove_options: the options need to be removed in this instruction.
        """
        super().__init__(instruction_index=instruction_index)
        self.command_index = command_index
        self.remove_options = remove_options

