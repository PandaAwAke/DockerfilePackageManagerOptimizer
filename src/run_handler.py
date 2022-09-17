import re

from global_status import GlobalStatus
from pm_handler import PMHandler


class RunHandler(object):
    def __init__(self, global_status: GlobalStatus):
        self.global_status = global_status
        self.pm_handler = PMHandler(global_status=global_status)
        self.user_and_userdir = {}

    def handle(self, command: str, instruction_index: int):
        commands = self._split_commands(command)
        # Now we got all commands in this RUN instruction!
        need_pm_handler = False
        for command in commands:
            if len(command) == 0:
                continue
            executable = command[0]
            # Handle useradd/usermod
            if executable == 'useradd':
                self._handle_useradd(command)
            elif executable == 'usermod':
                self._handle_usermod(command)
            # Handle Package Manager Command
            elif self.pm_handler.is_package_manager_executable(executable):
                need_pm_handler = True
            # TODO: Handle Shell Script
            else:
                ...
        if need_pm_handler:
            self.pm_handler.handle(commands=commands, instruction_index=instruction_index)

    @staticmethod
    def _split_commands(command: str) -> list:
        words = command.split()
        # Separate multiple commands in single command line, for example 'a && b || c'
        commands = []
        command = []
        brackets_re = re.compile(r'^\(*(.*?)\)*$')
        for word in words:
            # Greedy strategy: All commands (whether or not they will be executed at runtime) are considered.
            if word == '&&' or word == ';' or word == '||':  # TODO: Consider > and |
                # We do not care if some commands are surrounded by brackets
                commands.append(command)
                command = []
            else:
                word_removed_brackets = brackets_re.match(word).group(1)
                command.append(word_removed_brackets)
        if len(command) > 0:
            commands.append(command)
        return commands

    def _handle_useradd(self, command: list):
        arg_home_dir = False    # -d, --home-dir
        arg_base_dir = False    # -b, --base-dir
        user_home_dir = ''
        user_base_dir = ''
        user_name = command[-1]
        for word in command[1:]:
            if word == '-d' or word == '--home-dir':
                arg_home_dir = True
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
        user_name = command[-1]
        for word in command[1:]:
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
