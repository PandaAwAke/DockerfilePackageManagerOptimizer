import logging

import yaml
import re

from model import handle_error
from model.global_status import GlobalStatus
from optimize.optimization_strategy import *


class PMSetting(object):
    def __init__(self, executables: list = None,
                 commands_regex_run: list = None,
                 default_cache_dirs: list = None,
                 commands_regex_modify_cache_dir: list = None,
                 additional_pre_commands: list = None):
        self.executables = executables
        self.commands_regex_run = commands_regex_run
        self.default_cache_dirs = default_cache_dirs
        self.commands_regex_modify_cache_dir = commands_regex_modify_cache_dir
        self.additional_pre_commands = additional_pre_commands


class PMStatus(object):
    def __init__(self, cache_dirs=None):
        self.cache_dirs = cache_dirs
        self.pre_commands_added = False


pm_settings = {}


def load_pm_settings():
    if len(pm_settings) > 0:
        return
    try:
        f = open(file='resources/PMSettings.yaml', mode='r', encoding='utf-8')
        pm_yaml_settings = yaml.safe_load(f)
    except Exception as e:  # Including: IOError, yaml.YAMLError
        logging.error(e)
        raise handle_error.HandleError()
    pm_yaml_settings: dict = pm_yaml_settings['packageManagers']
    for pm_name in pm_yaml_settings.keys():
        pm_yaml_dict: dict = pm_yaml_settings[pm_name]
        pm_setting = PMSetting(
            executables=pm_yaml_dict.get('executables') or [pm_name],
            commands_regex_run=pm_yaml_dict.get('commands-regex-run') or [],
            default_cache_dirs=pm_yaml_dict.get('default-cache-dirs') or [],
            commands_regex_modify_cache_dir=pm_yaml_dict.get('commands-regex-modify-cache-dir') or [],
            additional_pre_commands=pm_yaml_dict.get('additional-pre-commands') or []
        )
        if len(pm_setting.commands_regex_run) == 0:
            logging.error('commands-regex-run is not set for "{0}"!'.format(pm_name))
            exit(-1)
        if len(pm_setting.default_cache_dirs) == 0:
            logging.error('default-cache-dirs is not set for "{0}"!'.format(pm_name))
            exit(-1)
        pm_settings[pm_name] = pm_setting
    f.close()


class PMHandler(object):

    def __init__(self, global_status: GlobalStatus):
        self.global_status = global_status
        self.pm_statuses = {}
        self.optimization_strategies = []
        load_pm_settings()

    @staticmethod
    def is_package_manager_executable(executable: str) -> bool:
        for pm_name, pm_setting in pm_settings.items():
            if executable in pm_setting.executables:
                return True
        return False

    def handle(self, commands: list, instruction_index: int):
        need_optimization_pm_names = []
        for command in commands:
            executable = command[0].s
            for pm_name, pm_setting in pm_settings.items():
                if executable in pm_setting.executables:
                    break
            else:
                continue
            if pm_name not in self.pm_statuses.keys():
                self.pm_statuses[pm_name] = PMStatus(
                    cache_dirs=[self._replace_home_char(cache_dir)
                                for cache_dir in pm_settings[pm_name].default_cache_dirs]
                )
            pm_status: PMStatus = self.pm_statuses[pm_name]
            command_str = ' '.join([word.s for word in command[1:]])

            # Case for modifying the cache dir
            for command_regex_modify_cache_dir in pm_settings[pm_name].commands_regex_modify_cache_dir:
                modify_cache_dir_re = re.compile(command_regex_modify_cache_dir)
                match_result = modify_cache_dir_re.match(command_str)
                # Only considering one match! So we will return directly once finished handling the match.
                if match_result and len(match_result.groups()) > 0:  # This command will modify the cache dir
                    pm_status.cache_dirs = []
                    for new_cache_dir in match_result.groups():
                        new_cache_dir = self._replace_home_char(new_cache_dir).strip()
                        if not new_cache_dir.startswith('/'):  # Relative path, need to use WORKDIR
                            new_cache_dir = self.global_status.work_dir + new_cache_dir
                        pm_status.cache_dirs.append(new_cache_dir)
                    return
                # TODO: Consider more conditions for modifying cache dir

            # Case for running the package manager's build/install process
            for command_regex_run in pm_settings[pm_name].commands_regex_run:
                run_re = re.compile(command_regex_run)
                match_result = run_re.match(command_str)
                # Only considering one match
                if match_result:
                    need_optimization_pm_names.append(pm_name)

        # ** Note: Don't generate duplicated strategies for a single instruction including multiple commands!
        insert_before_strategy = None
        add_cache_strategy = None

        for pm_name in need_optimization_pm_names:
            # Generate optimization strategies Try to generate InsertBeforeStrategy
            # Note: additional_pre_commands are only added once in a stage!
            #   This means that multiple apt-get instructions will result in only once command addition
            if len(pm_settings[pm_name].additional_pre_commands) > 0 and \
                    not self.pm_statuses[pm_name].pre_commands_added:
                if insert_before_strategy is None:
                    insert_before_strategy = InsertBeforeStrategy(instruction_index, [])
                for additional_pre_command in pm_settings[pm_name].additional_pre_commands:
                    if additional_pre_command not in insert_before_strategy.commands_insert:
                        insert_before_strategy.commands_insert.append(additional_pre_command)
                self.pm_statuses[pm_name].pre_commands_added = True

            # Generate AddCacheStrategy
            if add_cache_strategy is None:
                add_cache_strategy = AddCacheStrategy(instruction_index, [])
            for cache_dir in self.pm_statuses[pm_name].cache_dirs:
                if cache_dir not in add_cache_strategy.cache_dirs:
                    add_cache_strategy.cache_dirs.append(cache_dir)

        if insert_before_strategy is not None:
            self.optimization_strategies.append(insert_before_strategy)
        if add_cache_strategy is not None:
            self.optimization_strategies.append(add_cache_strategy)

    def _replace_home_char(self, path: str) -> str:
        """
        Replace '~' in the directory path.
        :return: replaced path
        """
        return path.replace('~', self.global_status.user_dirs[self.global_status.user][:-1])
