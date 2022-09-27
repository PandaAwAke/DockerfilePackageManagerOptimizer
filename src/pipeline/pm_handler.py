import logging
import re

import yaml

import config
from model import handle_error
from model.global_status import GlobalStatus
from model.optimization_strategy import *


class PMSetting(object):
    """
    The settings for a package manager, read from "PMSettings.yaml".
    """

    def __init__(self, executables: list = None,
                 commands_regex_run: list = None,
                 default_cache_dirs: list = None,
                 commands_regex_modify_cache_dir: list = None,
                 additional_pre_commands: list = None):
        """
        Initialize the PM's settings.

        :param executables: the executables of this PM, for example: [apt, apt-get, ...] for apt.
        :param commands_regex_run: the regular expressions for running the PM download/install/compile commands.
        :param default_cache_dirs: the default download cache directories for this PM
                ("~" inside the filepath is also supported and recommended).
        :param commands_regex_modify_cache_dir: (Nullable) the regular expressions for modifying the
                PM cache directories commands. Group 1 of the regex is the new filepath.
        :param additional_pre_commands: (Nullable) the commands need to be added before all this PM related commands.
        """
        self.executables = executables
        self.commands_regex_run = commands_regex_run
        self.default_cache_dirs = default_cache_dirs
        self.commands_regex_modify_cache_dir = commands_regex_modify_cache_dir
        self.additional_pre_commands = additional_pre_commands


pm_settings = {}    # All PM's settings. Key: PM's name; Value: a PMSetting object.


def load_pm_settings():
    """
    Load all PM settings from "PMSettings.yaml" into pm_settings.

    :return: None
    """
    if len(pm_settings) > 0:
        return
    try:
        f = open(file=config.global_settings.pm_settings_path, mode='r', encoding='utf-8')
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
    """
    Maintain a PMStatus for every PM and try to generate OptimizationStrategies
        (pipeline.optimize.optimization_strategy).

    -   Take pm-related commands from RunHandler and try to handle them.
    -   When this instruction can be optimized, try to generate optimization strategies.
    """

    class PMStatus(object):
        """
        The status for a PM. Created when this PM is firstly encountered.
        """
        def __init__(self, cache_dirs=None):
            self.cache_dirs = cache_dirs
            self.pre_commands_added = False

    def __init__(self, global_status: GlobalStatus):
        """
        Initialize the PMHandler.

        :param global_status: the global_status of this stage created by stage simulator.
        """
        self.global_status = global_status
        self.pm_statuses = {}   # Key: PM's name; Value: PMStatus object
        self.optimization_strategies = []
        load_pm_settings()

    @staticmethod
    def is_package_manager_executable(executable: str) -> bool:
        """
        This function is used by RunHandler to determine if the executable is a PM executable.

        :param executable: the executable of a command.
        :return: True when executable is a PM executable, or else False.
        """
        for pm_name, pm_setting in pm_settings.items():
            if executable in pm_setting.executables:
                return True
        return False

    @staticmethod
    def _get_executable_package_manager(executable: str):
        """
        Similar to is_package_manager_executable(), but return the PM's name.

        :param executable: the executable of a command.
        :return: the PM's name when executable is a PM executable, or else None.
        """
        for pm_name, pm_setting in pm_settings.items():
            if executable in pm_setting.executables:
                return pm_name
        return None

    def handle(self, commands: list, instruction_index: int):
        """
        Handle a list of commands from RunHandler.

        :param commands: all PM-related commands inside this instruction.
        :param instruction_index: the index of this instruction.
        :return: None
        """
        need_optimization_pm_names = []

        # -------------------- Handling PM-related commands --------------------
        for command in commands:
            assert len(command) > 0
            # if len(command) == 0:
            #     logging.error("This dockerfile is too complex, I can't handle it now.")
            #     raise handle_error.HandleError()
            executable = command[0].s
            pm_name = self._get_executable_package_manager(executable)

            if pm_name not in self.pm_statuses.keys():  # Firstly encountered this PM, create a PMStatus
                self.pm_statuses[pm_name] = PMHandler.PMStatus(
                    cache_dirs=[self._replace_home_char(cache_dir)
                                for cache_dir in pm_settings[pm_name].default_cache_dirs]
                )
            pm_status: PMHandler.PMStatus = self.pm_statuses[pm_name]

            # Concatenate the command words as string to match the regexes.
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

        # -------------------- Generating optimization strategies --------------------
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

        :param path: the path to be replaced.
        :return: replaced path.
        """
        return path.replace('~', self.global_status.user_dirs[self.global_status.user][:-1])
