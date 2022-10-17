import logging
import re

from config import optimization_config
from model import handle_error
from model.command_word import CommandWord
from model.global_status import GlobalStatus
from model.optimization_strategy import RemoveCommandStrategy
from pipeline.pm_handler import PMHandler
from util import str_util, shell_util


class RunHandler(object):
    """
    Take a RUN instruction from Stage Simulator, and parse the commands inside the instruction.
    Package-manager-related and global-status-related commands are considered.

    -   Note that a RUN instruction can consist of multiple commands, such as
        "RUN apt-get update && apt-get install gcc".
    -   All package-manager-related commands will be passed to PMHandler.
    """

    def __init__(self, global_status: GlobalStatus, optimization_strategies):
        """
        Initialize the RunHandler.

        :param global_status: the global_status of this stage created by stage simulator.
        """
        self.global_status = global_status
        self.pm_handler = PMHandler(global_status=global_status, optimization_strategies=optimization_strategies)
        self.optimization_strategies = optimization_strategies

    def handle(self, commands_str: str, context, instruction_index: int):
        """
        Handle the commands string after "RUN".
        -   All package-manager-related commands will be passed to PMHandler.

        :param commands_str: the commands string after "RUN"
                            (preprocessed by DockerfileParse, so line_continue_char does not exist).
        :param context: the context object of this instruction.
        :param instruction_index: the instruction index of the stage.
        :return: None
        """
        # Pay attention to RUN options, such as RUN --mount, this should be ignored
        _, commands_str = str_util.separate_run_options(commands_str)

        if shell_util.is_exec_form(commands_str):
            commands = self._process_exec_form(commands_str)
        else:
            commands, _ = shell_util.process_shell_form(commands_str, context)
        commands = self._handle_bash_c(commands, context)

        pm_related_commands = []
        remove_command_indices = []
        # Now we got all commands in this RUN instruction!
        for index in range(len(commands)):
            command_words = commands[index]
            if len(command_words) == 0:
                continue
            executable = command_words[0].s
            # Handle useradd/usermod
            if executable == 'useradd':
                self._handle_useradd(command_words)
            elif executable == 'usermod':
                self._handle_usermod(command_words)
            # Handle Package Manager Command
            elif self.pm_handler.is_package_manager_executable(executable):
                pm_related_commands.append(command_words)
            # TODO: Handle Shell Script

            if self._need_remove_anti_cache_commands(command_words):
                remove_command_indices.append(index)

        if len(pm_related_commands) > 0:
            self.pm_handler.handle(commands=pm_related_commands, instruction_index=instruction_index)
            # self.pm_handler.handle(commands=commands, instruction_index=instruction_index)

        # --------------- Generate RemoveCommandStrategy ---------------
        if len(remove_command_indices) > 0:
            remove_command_strategy = RemoveCommandStrategy(instruction_index, remove_command_indices)
            self.optimization_strategies.append(remove_command_strategy)

    @staticmethod
    def _process_exec_form(commands_str: str):
        """
        Preprocess the commands_str behind RUN (exec-form).
        ENV variables won't be substituted here.

        :param commands_str: the exec-form command string, for example '["echo", "hello, world!"]'
        :return: a single-member list of: list of processed CommandWords when commands_str is exec-form;
                    (For example,
                        [[CommandWord('bash'), CommandWord('-c'),
                         CommandWord('echo'), CommandWord('hello world!')]]
                    )
                    or None when commands_str isn't exec-form.
                    A single-member list of list is returned because it's consistent with the shell-form
                    processing (a list of commands, a command is a list of CommandWords).
        """
        # Handling exec-form
        exec_form_re = re.compile(r'^\s*(\[[\s\S]*])\s*$')
        match_result = exec_form_re.match(commands_str)
        if match_result is not None:
            # Exec form, let's eval
            try:
                command_words = eval(match_result.group(1))  # ["bash", "-c", "echo", "hello world!"]
            except Exception as e:
                logging.error('Illegal RUN exec-form: "{0}"'.format(commands_str))
                raise handle_error.HandleError()
            return [[CommandWord(word, CommandWord.EXEC_FORM_ARG) for word in command_words]]
        else:
            return None

    # --------------------- Handling executables ---------------------

    @staticmethod
    def _handle_bash_c(commands: list, context) -> list:
        """
        Detect and process the '/bin/bash -c "command"' situation.
        Each command of commands will be processed.

        :param commands: a list of commands to be processed inside this instruction.
        :param context: the context of this instruction.
        :return: a list of processed commands.
        """
        # Handle "/bin/bash -c command"
        new_commands = []
        for command_words in commands:
            if not (len(command_words) > 1 and command_words[0].s.lower() in ('bash', 'sh', '/bin/bash', '/bin/sh')):
                new_commands.append(command_words)
                continue
            # The executable is sh/bash, let's translate -c
            for i in range(1, len(command_words)):
                command_word = command_words[i]
                if command_word.s == '-c' and i < len(command_words) - 1:
                    real_commands_str = command_words[i + 1].s
                    real_commands_words, _ = shell_util.process_shell_form(real_commands_str, context)
                    new_commands.extend(real_commands_words)
                    break
        return new_commands

    def _handle_useradd(self, command: list):
        """
        Handle "useradd" command, update global_status.

        :param command: a list of CommandWords.
        :return: None
        """
        arg_home_dir = False    # -d, --home-dir
        arg_base_dir = False    # -b, --base-dir
        user_home_dir = ''
        user_base_dir = ''
        user_name = command[-1].s
        for command_word in command[1:]:
            word = command_word.s
            if word == '-d' or word == '--home-dir':
                arg_home_dir = True     # Next word is home_dir
            elif arg_home_dir:
                user_home_dir = word if word.endswith('/') else word + '/'
                arg_home_dir = False
            elif word == '-b' or word == '--base-dir':
                arg_base_dir = True
            elif arg_base_dir:
                user_base_dir = word if word.endswith('/') else word + '/'
                arg_base_dir = False
        if user_home_dir != '':
            real_user_home = user_home_dir
        elif user_base_dir != '':
            real_user_home = user_base_dir + user_name + '/'
        else:
            if user_name != 'root':
                real_user_home = '/home/' + user_name + '/'
            else:
                real_user_home = '/root/'
        self.global_status.user_dirs[user_name] = real_user_home

    def _handle_usermod(self, command: list):
        """
        Handle "usermod" command, update global_status.

        :param command: a list of CommandWords.
        :return: None
        """
        arg_home_dir = False    # -d, --home
        user_home_dir = ''
        user_name = command[-1].s
        for command_word in command[1:]:
            word = command_word.s
            if word == '-d' or word == '--home':
                arg_home_dir = True
            elif arg_home_dir:
                user_home_dir = word if word.endswith('/') else word + '/'
                arg_home_dir = False
        if user_home_dir != '':
            real_user_home = user_home_dir
        else:
            if user_name != 'root':
                real_user_home = '/home/' + user_name + '/'
            else:
                real_user_home = '/root/'
        self.global_status.user_dirs[user_name] = real_user_home

    @staticmethod
    def _need_remove_anti_cache_commands(command: list):
        """
        Check if this command is an anti-cache command.
        :param command: the command to check.
        :return: True if this command is an anti-cache command, or else False.
        """
        # Case for removing anti-cache commands
        for command_regex_anti_cache in optimization_config.global_opt_settings.anti_cache_commands_regex:
            anti_cache_re = re.compile(command_regex_anti_cache)
            command_str = str_util.join_command_words(command)
            match_result = anti_cache_re.match(command_str)
            if match_result:
                return True
        return False

