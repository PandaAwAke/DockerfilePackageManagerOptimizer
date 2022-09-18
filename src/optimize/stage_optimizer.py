import logging
import re

from model import handle_error
from optimize.optimization_strategy import *

from model.stats import stats


class StageOptimizer(object):

    def __init__(self, instructions):
        self.new_stage_lines = []
        self.instructions = instructions

    def optimize(self, optimization_strategies: list) -> list:
        if len(optimization_strategies) == 0:
            return [instruction['content'] for instruction in self.instructions]

        self.new_stage_lines = []
        optimization_indices = [strategy.instruction_index for strategy in optimization_strategies]
        instruction_index = 0
        """
        Instructions are like:
        [
            {"instruction": "FROM",       # always upper-case
             "startline": 0,              # 0-based
             "endline": 0,                # 0-based
             "content": "From fedora\n",
             "value": "fedora"},

            {"instruction": "CMD",
             "startline": 1,
             "endline": 2,
             "content": "CMD yum -y update && \\\n    yum clean all\n",
             "value": "yum -y update && yum clean all"}
        ]
        """
        last_instruction = None
        for instruction in self.instructions:
            # Save the original dockerfile layout as much as possible
            if last_instruction is not None and last_instruction['endline'] != -1:
                empty_lines = instruction['startline'] - last_instruction['endline'] - 1
                if empty_lines > 0:
                    self.new_stage_lines.append('\n' * empty_lines)
            if instruction_index in optimization_indices:
                matched_strategies = [strategy for strategy in optimization_strategies
                                      if strategy.instruction_index == instruction_index]
                # Note: if an instruction doesn't use AddCacheStrategy, then it also need to be copied
                need_to_copy = True
                for strategy in matched_strategies:
                    if isinstance(strategy, AddCacheStrategy):  # At most 1 AddCacheStrategy one instruction
                        self._optimize_add_cache(strategy=strategy, instruction=instruction)
                        need_to_copy = False
                    elif isinstance(strategy, InsertBeforeStrategy):
                        self._optimize_insert_before(strategy=strategy, last_instruction=last_instruction)
                if need_to_copy:
                    self.new_stage_lines.append(instruction['content'])
            else:
                self.new_stage_lines.append(instruction['content'])
            instruction_index += 1
            last_instruction = instruction
        return self.new_stage_lines

    def _optimize_add_cache(self, strategy: AddCacheStrategy, instruction: dict):
        if instruction['instruction'] != 'RUN':
            logging.error('Tried to optimize a non-RUN instruction: "{0}"'.format(instruction['content']))
            raise handle_error.HandleError()

        # Search if there's already "--mount=type=cache" inside the command
        # Note that stripped_command has no line_continuation_char or new_line_char!
        stripped_command: str = instruction['value']
        find_index: int = 0
        find_index = stripped_command.find('--mount=type=cache', find_index)
        existing_target_dirs = []
        while find_index != -1:
            target_dir_index = stripped_command.find('target=', find_index)
            if target_dir_index == -1:
                logging.error('Cannot find the target directory in existing --mount=type=cache RUN instruction: '
                              '"{0}"'.format(instruction['content']))
                raise handle_error.HandleError()
            # Get target_dir
            space_index = stripped_command.find(' ', target_dir_index)
            if space_index == -1:
                logging.error('Illegal --mount=type=cache instruction format: '
                              '"{0}"'.format(instruction['content']))
                raise handle_error.HandleError()
            target_dir = stripped_command[target_dir_index + len('target='):space_index]
            existing_target_dirs.append(target_dir)

            find_index = stripped_command.find('--mount=type=cache', find_index + len('--mount=type=cache'))

        # Create new instruction: add --mount=type=cache for those non-mounted directories
        non_mounted_cache_dirs = [cache_dir for cache_dir in strategy.cache_dirs
                                  if cache_dir not in existing_target_dirs]
        mount_args = ['--mount=type=cache,target={0}'.format(cache_dir) for cache_dir in non_mounted_cache_dirs]
        mount_args_str = ' '.join(mount_args)

        inst_re = re.compile(r'^\s*(\S+)\s+([\s\S]*)$')
        m = inst_re.match(instruction['content'])
        inst_body = m.group(2)
        new_content = ' '.join([
            instruction['instruction'],
            mount_args_str,
            inst_body
        ])
        self.new_stage_lines.append(new_content)
        stats.add_cache()        # Stats

    def _optimize_insert_before(self, strategy: InsertBeforeStrategy, last_instruction: dict):
        for command_insert in strategy.commands_insert:
            # Avoid inserting the same instruction
            if (last_instruction is None) or \
                    (last_instruction is not None and last_instruction['value'] != command_insert):
                self.new_stage_lines.append('RUN ' + command_insert + '\n')
                stats.insert_before()    # Stats
