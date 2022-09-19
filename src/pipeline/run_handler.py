import logging
import re

from model.global_status import GlobalStatus
from model import handle_error
from model.command_word import CommandWord
from pipeline.pm_handler import PMHandler


class RunHandler(object):
    def __init__(self, global_status: GlobalStatus):
        self.global_status = global_status
        self.pm_handler = PMHandler(global_status=global_status)
        self.user_and_userdir = {}

    def handle(self, command_str: str, instruction_index: int):
        # Pay attention to RUN options, such as RUN --mount, this should be ignored
        command_str = self._remove_run_options(command_str)
        commands = self._process_exec_form(command_str)
        if commands is None:
            commands = self._process_shell_form(command_str)
        commands = self._handle_bash_c(commands)
        # Now we got all commands in this RUN instruction!
        need_pm_handler = False
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
                need_pm_handler = True
            # TODO: Handle Shell Script
            else:
                ...
        if need_pm_handler:
            self.pm_handler.handle(commands=commands, instruction_index=instruction_index)

    # --------------------- PreProcessing ---------------------

    @staticmethod
    def _remove_run_options(command_str: str) -> str:
        # Remove RUN options, such as --mount=type=cache
        remove_run_option_re = re.compile('^\s*(--\S+\s*)*([\s\S]*?)\s*$')
        match_result = remove_run_option_re.match(command_str)
        assert match_result is not None and match_result.group(2) is not None
        return match_result.group(2)

    @staticmethod
    def _process_exec_form(command_str: str):
        # Handling exec-form
        exec_form_re = re.compile(r'^\s*(\[[\s\S]*])\s*$')
        match_result = exec_form_re.match(command_str)
        if match_result is not None:
            # Exec form, let's eval
            try:
                command_words = eval(match_result.group(1))  # ['bash', '-c', 'echo', 'hello world!']
            except Exception as e:
                logging.error('Illegal RUN exec-form: "{0}"'.format(command_str))
                raise handle_error.HandleError()
            return [[CommandWord(word, CommandWord.EXEC_FORM_ARG) for word in command_words]]
        else:
            return None

    @staticmethod
    def _process_shell_form(command_str: str) -> list:
        """
        Preprocess the command_str behind RUN (shell-form).
        all commands inside command_str (connected with &&, ||, etc) will be returned.
        Note: escape character will not be translated inside double quotes, but \" inside
              double quotes can be recognized.

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
        :param command_str:
        :return: List of commands. A command is a list of CommandWords.
        """
        # Handling shell-form
        command_str_split_words = []
        # Pay attention to quotes and brackets!
        # - Find quotes
        i = 0
        s = ''
        while i < len(command_str):
            if command_str[i] == "'":
                matched_quote = command_str.find("'", i + 1)    # Find matched quote
                if matched_quote == -1:
                    logging.error('Illegal RUN command: "{0}"'.format(command_str))
                    raise handle_error.HandleError()
                content_inside_quote = command_str[i + 1: matched_quote]
                # Remove brackets directly, because we don't care about the order of evaluation
                command_str_split_words.extend([CommandWord(word) for word in s.replace('(', '').replace(')', '').split()])
                s = ''
                command_str_split_words.append(CommandWord(content_inside_quote, CommandWord.SINGLE_QUOTED))
                i = matched_quote
            elif command_str[i] == '"':
                j = i + 1
                while True:
                    matched_quote = command_str.find('"', j)  # Find matched quote
                    if matched_quote == -1:
                        logging.error('Illegal RUN command: "{0}"'.format(command_str))
                        raise handle_error.HandleError()
                    if command_str[matched_quote - 1] != '\\':
                        break
                    else:
                        j = matched_quote + 1

                content_inside_quote = command_str[i + 1: matched_quote]
                command_str_split_words.extend([CommandWord(word) for word in s.replace('(', '').replace(')', '').split()])
                s = ''
                command_str_split_words.append(CommandWord(content_inside_quote, CommandWord.DOUBLE_QUOTED))
                i = matched_quote
            else:
                s += command_str[i]
            i += 1
        if len(s) > 0:
            command_str_split_words.extend([CommandWord(word) for word in s.replace('(', '').replace(')', '').split()])

        # - Separate multiple commands in command_str, for example 'a && b || c'
        commands = []
        command_words = []
        for command_word in command_str_split_words:
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

    def _handle_bash_c(self, commands: list) -> list:
        # Handle "/bin/bash -c command"
        new_commands = []
        for command_words in commands:
            if not (len(command_words) > 1 and command_words[0].s.lower() in ('bash', 'sh', '/bin/bash', '/bin/sh')):
                new_commands.append(command_words)
                continue
            # The executable is sh/bash, let's translate -c
            # TODO: Translate ENV
            for i in range(1, len(command_words)):
                command_word = command_words[i]
                if command_word.s == '-c' and i < len(command_words) - 1:
                    real_command_str = command_words[i + 1].s
                    real_command_words = self._process_shell_form(real_command_str)
                    new_commands.extend(real_command_words)
                    break
        return new_commands

    # --------------------- Handling executables ---------------------

    def _handle_useradd(self, command: list):
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
