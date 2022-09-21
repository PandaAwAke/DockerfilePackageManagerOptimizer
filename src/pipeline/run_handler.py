import logging
import re

import utils
from model import handle_error
from model.command_word import CommandWord
from model.global_status import GlobalStatus
from pipeline.pm_handler import PMHandler


class RunHandler(object):
    """
    Take a RUN instruction from Stage Simulator, and parse the commands inside the instruction.
    Package-manager-related and global-status-related commands are considered.
    -   Note that a RUN instruction can consist of multiple commands, such as
        "RUN apt-get update && apt-get install gcc".
    -   All package-manager-related commands will be passed to PMHandler.
    """

    def __init__(self, global_status: GlobalStatus):
        """
        Initialize the RunHandler.
        :param global_status: the global_status of this stage created by stage simulator.
        """
        self.global_status = global_status
        self.pm_handler = PMHandler(global_status=global_status)

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
        commands_str = self._remove_run_options(commands_str)
        commands = self._process_exec_form(commands_str)
        if commands is None:
            commands = self._process_shell_form(commands_str, context)
        commands = self._handle_bash_c(commands, context)
        pm_related_commands = []
        # Now we got all commands in this RUN instruction!
        for command_words in commands:
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
            else:
                ...
        if len(pm_related_commands) > 0:
            self.pm_handler.handle(commands=pm_related_commands, instruction_index=instruction_index)

    # --------------------- PreProcessing ---------------------
    @staticmethod
    def _remove_brackets(s: str) -> str:
        return s.replace('(', '').replace(')', '')

    @staticmethod
    def _remove_run_options(commands_str: str) -> str:
        # Remove RUN options, such as --mount=type=cache
        remove_run_option_re = re.compile('^\s*(--\S+\s*)*([\s\S]*?)\s*$')
        match_result = remove_run_option_re.match(commands_str)
        assert match_result is not None and match_result.group(2) is not None
        return match_result.group(2)

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

    def _process_shell_form(self, commands_str: str, context) -> list:
        """
        Preprocess the commands_str behind RUN (shell-form).
        all commands inside commands_str (connected with &&, ||, etc) will be returned.
        Note: escape character will not be translated inside double quotes, but \" inside
              double quotes can be recognized.
              ENV variables are substituted too (including string inside double quotes).

        Examples:
        ->  apt-get install python3-pip && echo "hello, world!"
        <-  [
                [CommandWord('apt-get'), CommandWord('install'), CommandWord('python3-pip')],
                [CommandWord('echo'), CommandWord('hello, world!')]
            ]
        ->  echo 'ab\"cd' && echo "ab\"cd"
        <-  [
                [CommandWord('echo'), CommandWord('ab\\"cd', SINGLE_QUOTED)],
                [CommandWord('echo'), CommandWord('ab\\"cd', DOUBLE_QUOTED)]
            ]

        :param commands_str: the shell-form commands string, for example 'apt-get update && apt install gcc'
        :param context: the context of this instruction. Context can be None.
        :return: List of commands. A command is a list of CommandWords.
        """
        # Handling shell-form
        commands_str_split_words = []

        # - Handling quotes and brackets
        i = 0
        content_outside_quote = ''
        while i < len(commands_str):
            if commands_str[i] == "'":
                matched_quote = commands_str.find("'", i + 1)    # Find matched quote
                if matched_quote == -1:
                    logging.error('Illegal RUN command: "{0}"'.format(commands_str))
                    raise handle_error.HandleError()

                # Remove brackets directly, because we don't care about the order of evaluation
                content_outside_quote = self._remove_brackets(content_outside_quote)
                content_outside_quote = utils.substitute_env(content_outside_quote, context)
                commands_str_split_words.extend([
                    CommandWord(word) for word in content_outside_quote.split()
                ])
                content_outside_quote = ''

                content_inside_quote = commands_str[i + 1: matched_quote]
                commands_str_split_words.append(CommandWord(content_inside_quote, CommandWord.SINGLE_QUOTED))
                i = matched_quote
            elif commands_str[i] == '"':
                j = i + 1
                while True:
                    matched_quote = commands_str.find('"', j)  # Find matched quote
                    if matched_quote == -1:
                        logging.error('Illegal RUN command: "{0}"'.format(commands_str))
                        raise handle_error.HandleError()
                    if commands_str[matched_quote - 1] != '\\':
                        break
                    else:
                        j = matched_quote + 1

                content_outside_quote = self._remove_brackets(content_outside_quote)
                content_outside_quote = utils.substitute_env(content_outside_quote, context)
                commands_str_split_words.extend([
                    CommandWord(word) for word in content_outside_quote.split()
                ])
                content_outside_quote = ''

                content_inside_quote = commands_str[i + 1: matched_quote]
                content_inside_quote = utils.substitute_env(content_inside_quote, context)
                commands_str_split_words.append(CommandWord(content_inside_quote, CommandWord.DOUBLE_QUOTED))
                i = matched_quote
            else:
                content_outside_quote += commands_str[i]
            i += 1
        if len(content_outside_quote) > 0:
            content_outside_quote = self._remove_brackets(content_outside_quote)
            content_outside_quote = utils.substitute_env(content_outside_quote, context)
            commands_str_split_words.extend([
                CommandWord(word) for word in content_outside_quote.split()
            ])

        # - Separate multiple commands in commands_str, for example 'a && b || c'
        commands = []
        command_words = []
        for command_word in commands_str_split_words:
            word = command_word.s
            # Greedy strategy: All commands (whether or not they will be executed at runtime) are considered.
            if word == '&&' or word == ';' or word == '||':  # TODO: Consider > and |
                # We do not care if some commands are surrounded by brackets
                commands.append(command_words)
                command_words = []
            else:
                command_words.append(command_word)
        if len(command_words) > 0:
            commands.append(command_words)
        return commands

    def _handle_bash_c(self, commands: list, context) -> list:
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
                    real_commands_words = self._process_shell_form(real_commands_str, context)
                    new_commands.extend(real_commands_words)
                    break
        return new_commands

    # --------------------- Handling executables ---------------------

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
