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
from config.engine_config import engine_settings
from model.optimization_strategy import *
from model.stats import stats
from util import str_util, context_util, shell_util


class StageOptimizer(object):
    """
    Try to apply all optimization strategies from PMHandler to the stage.
    """

    def __init__(self, stage, lines):
        """
        Initialize the optimizer.

        :param stage: the stage to optimize.
        """
        self.new_stage_lines = []
        self.instructions, self.contexts = stage
        self.lines = lines

    def optimize(self, optimization_strategies: list) -> list:
        """
        Optimize the stage using optimization_strategies.

        :param optimization_strategies: a list of OptimizationStrategies from PMHandler.
        :return: a list of string lines describing the optimized stage.
        """
        if len(optimization_strategies) == 0:
            return [instruction['content'] for instruction in self.instructions]

        self.new_stage_lines = []   # The string lines of new dockerfile
        optimization_instruction_indices = [strategy.instruction_index for strategy in optimization_strategies]
        instruction_index = 0
        pre_instruction = None
        for i in range(len(self.instructions)):
            instruction = self.instructions[i]
            context = self.contexts[i]
            # Save the original dockerfile layout as much as possible
            if pre_instruction is not None and pre_instruction['endline'] != -1:
                empty_lines = instruction['startline'] - pre_instruction['endline'] - 1
                if empty_lines > 0:
                    self.new_stage_lines.append('\n' * empty_lines)
            if instruction_index in optimization_instruction_indices:
                matched_strategies = [strategy for strategy in optimization_strategies
                                      if strategy.instruction_index == instruction_index]
                # Note: if an instruction doesn't use AddCacheStrategy, then it also need to be copied
                for strategy in matched_strategies:
                    if isinstance(strategy, AddCacheStrategy):  # At most 1 AddCacheStrategy one instruction
                        self._optimize_add_cache(strategy=strategy, instruction=instruction, context=context)
                    elif isinstance(strategy, InsertBeforeStrategy):
                        self._optimize_insert_before(strategy=strategy, pre_instruction=pre_instruction)
                    elif isinstance(strategy, RemoveCommandStrategy):
                        self._optimize_remove_command(strategy=strategy, instruction=instruction)

                # Some operations may cause empty lines, this is to remove empty instructions
                if instruction['content'].strip() != instruction['instruction']:
                    self.new_stage_lines.append(instruction['content'].strip() + '\n')
            else:
                self.new_stage_lines.append(instruction['content'].strip() + '\n')
                # self.new_stage_lines.extend(
                #     self.lines[instruction['startline']: instruction['endline'] + 1]
                # )
            instruction_index += 1
            pre_instruction = instruction
        return self.new_stage_lines

    # --------------------------- Specific optimizations ---------------------------
    def _optimize_add_cache(self, strategy: AddCacheStrategy, instruction: dict, context):
        """
        Apply the AddCacheStrategy for the instruction.

        :param strategy: the AddCacheStrategy.
        :param instruction: the instruction to optimize.
        :param context: the context of the instruction.
        :return: None
        """
        assert instruction['instruction'] == 'RUN'

        # Search if there's already "--mount=type=cache" inside the command
        # Note that stripped_command has no line_continuation_char or new_line_char!
        existing_target_dirs = context_util.get_mount_target_dirs(instruction=instruction, context=context)

        # Create new instruction: add --mount=type=cache for those non-mounted directories
        non_mounted_cache_dirs = [cache_dir for cache_dir in strategy.cache_dirs
                                  if cache_dir not in existing_target_dirs]
        mount_args = ['--mount=type=cache,target={0}'.format(cache_dir) for cache_dir in non_mounted_cache_dirs]
        mount_args_str = ' '.join(mount_args)

        # Generate optimized commands string
        instruction_type, instruction_body = str_util.separate_instruction_type_body(instruction['content'])
        new_content = ' '.join([
            instruction_type,     # Type of instruction, such as "RUN"
            mount_args_str,
            instruction_body
        ])
        instruction['content'] = new_content
        stats.add_cache()        # Stats

    def _optimize_insert_before(self, strategy: InsertBeforeStrategy, pre_instruction: dict):
        """
        Apply the InsertBeforeStrategy for the instruction.

        :param strategy: the InsertBeforeStrategy.
        :param pre_instruction: the instruction before the insertion point. This is to avoid inserting
                duplicated commands. When try to optimize an optimized Dockerfile, this will be helpful.
        :return: None
        """
        for command_insert in strategy.commands_insert:
            # Avoid inserting the same instruction
            if (pre_instruction is None) or \
                    (pre_instruction is not None and pre_instruction['value'] != command_insert):
                self.new_stage_lines.append('RUN ' + command_insert + '\n')
                stats.insert_before()    # Stats
    
    def _optimize_remove_command(self, strategy: RemoveCommandStrategy, instruction: dict):
        """
        Apply the RemoveCommandStrategy for the instruction.

        :param strategy: the RemoveCommandStrategy.
        :param instruction: the instruction to optimize.
        :return: None
        """
        assert instruction['instruction'] == 'RUN'

        # Parse the commands string again
        instruction_type, instruction_body = str_util.separate_instruction_type_body(instruction['content'])
        instruction_options, instruction_body = str_util.separate_run_options(instruction_body)

        commands, connectors = shell_util.split_command_strings(instruction_body)
        assert len(connectors) == len(commands) - 1

        # Remove the specified command, and the connector behind it
        new_commands, new_connectors = [], []
        for index in range(len(connectors)):
            if index not in strategy.remove_command_indices:
                new_commands.append(commands[index])
                new_connectors.append(connectors[index])
            elif engine_settings.remove_command_with_true:
                new_commands.append(' true ')
                new_connectors.append(connectors[index])

        # If the last command needs to be removed, then remove the connector before it
        if len(commands) - 1 in strategy.remove_command_indices:
            # Maybe anti-cache command is the only command in the instruction
            if engine_settings.remove_command_with_true:
                new_commands.append(' true ')
            else:
                if len(new_connectors) > 0:
                    new_connectors.pop()
        else:
            new_commands.append(commands[-1])

        new_content = (instruction_type + " " +
                       (instruction_options + " " if instruction_options != "" else "") +
                       shell_util.connect_shell_command_string(new_commands, new_connectors)).strip()

        # Be careful of the line_continue_char
        while new_content.endswith('\\'):
            new_content = new_content[:-1].strip()

        instruction['content'] = new_content
        stats.remove_command()  # Stats
