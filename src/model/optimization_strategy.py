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
