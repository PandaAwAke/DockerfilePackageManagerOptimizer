import logging
import re

import yaml

import config
import utils
from model import handle_error
from model.global_status import GlobalStatus
from model.optimization_strategy import *


class PMSetting(object):
    """
    The settings for a package manager, read from "PMSettings.yaml".
    """

    def __init__(self, executables: list,
                 commands_regex_run: list,
                 default_cache_dirs: list,
                 commands_regex_modify_cache_dir: list = None,
                 additional_pre_commands: list = None,
                 anti_cache_commands_regex: list = None):
        """
        Initialize the PM's settings.

        :param executables: the executables of this PM, for example: [apt, apt-get, ...] for apt.
        :param commands_regex_run: the regular expressions for running the PM download/install/compile commands.
        :param default_cache_dirs: the default download cache directories for this PM
                ("~" inside the filepath is also supported and recommended).
        :param commands_regex_modify_cache_dir: (Nullable) the regular expressions for modifying the
                PM cache directories commands. Group 1 of the regex is the new filepath.
        :param additional_pre_commands: (Nullable) the commands need to be added before all this PM related commands.
        :param anti_cache_commands_regex: (Nullable) the regular expressions for anti-cache commands.
                This will be used to recognize and remove anti-cache commands when optimizing.
        """
        self.executables = executables
        self.commands_regex_run = commands_regex_run
        self.default_cache_dirs = default_cache_dirs
        self.commands_regex_modify_cache_dir = commands_regex_modify_cache_dir
        self.additional_pre_commands = additional_pre_commands
        self.anti_cache_commands_regex = anti_cache_commands_regex


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
            additional_pre_commands=pm_yaml_dict.get('additional-pre-commands') or [],
            anti_cache_commands_regex=pm_yaml_dict.get('anti_cache_commands_regex') or []
        )

        if len(pm_setting.commands_regex_run) == 0:
            logging.error('commands-regex-run is not set for "{0}"!'.format(pm_name))
            exit(-1)
            return
        if len(pm_setting.default_cache_dirs) == 0:
            logging.error('default-cache-dirs is not set for "{0}"!'.format(pm_name))
            exit(-1)
            return
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
        def __init__(self, cache_dirs=None, remove_command_indices=None):
            self.cache_dirs = cache_dirs
            self.pre_commands_added = False
            self.remove_command_indices = remove_command_indices

    def __init__(self, global_status: GlobalStatus):
        """
        Initialize the PMHandler.

        :param global_status: the global_status of this stage created by stage simulator.
        """
        self.global_status = global_status
        self.pm_statuses = {}   # Key: PM's name; Value: PMStatus object
        self.optimization_strategies = []
        load_pm_settings()

    def handle(self, commands: list, instruction_index: int):
        """
        Handle a list of commands from RunHandler.

        :param commands: all PM-related commands inside this instruction.
        :param instruction_index: the index of this instruction.
        :return: None
        """

        class OptimizationKinds:
            def __init__(self):
                self.need_add_cache = False
                self.need_remove_command = False

        # Key: pm_name, Value: [NeedAddCache(bool), NeedRemoveCommand(bool)]
        # For example: {"npm": [True, False]}
        optimization_dict = {}

        # -------------------- Handling PM-related commands --------------------
        for command_index in range(len(commands)):
            command = commands[command_index]

            assert len(command) > 0     # Ensured by run_handler.handle()
            executable = command[0].s
            pm_name = self._get_executable_package_manager(executable)

            # If firstly encountered this PM, create a PMStatus
            if pm_name not in self.pm_statuses.keys():
                self.pm_statuses[pm_name] = PMHandler.PMStatus(
                    cache_dirs=[utils.replace_home_char(cache_dir, self.global_status)
                                for cache_dir in pm_settings[pm_name].default_cache_dirs]
                )

            # Concatenate the command words as string to match the regexes.
            command_str = ' '.join([word.s for word in command[1:]])

            pm_setting: PMSetting
            pm_status: PMHandler.PMStatus

            pm_setting = pm_settings[pm_name]
            pm_status = self.pm_statuses[pm_name]

            # ------------------------ Regex matching ------------------------
            # Case for modifying the cache dir
            for command_regex_modify_cache_dir in pm_setting.commands_regex_modify_cache_dir:
                modify_cache_dir_re = re.compile(command_regex_modify_cache_dir)
                match_result = modify_cache_dir_re.match(command_str)
                # Only considering one match! So we will return directly once finished handling the match.
                if match_result and len(match_result.groups()) > 0:  # This command will modify the cache dir
                    pm_status.cache_dirs = []
                    for new_cache_dir in match_result.groups():
                        new_cache_dir = utils.replace_home_char(new_cache_dir, self.global_status).strip()
                        new_cache_dir = utils.get_absolute_path(new_cache_dir, self.global_status)
                        pm_status.cache_dirs.append(new_cache_dir)
                    return
                # TODO: Consider more conditions for modifying cache dir

            # Case for running the package manager's build/install process
            for command_regex_run in pm_setting.commands_regex_run:
                run_re = re.compile(command_regex_run)
                match_result = run_re.match(command_str)
                # Only considering one match
                if match_result:
                    if optimization_dict.get(pm_name) is None:
                        optimization_dict[pm_name] = OptimizationKinds()
                    optimization_dict[pm_name].need_add_cache = True

            # Case for removing anti-cache commands
            for command_regex_anti_cache in pm_setting.anti_cache_commands_regex:
                anti_cache_re = re.compile(command_regex_anti_cache)
                match_result = anti_cache_re.match(command_str)
                if match_result:
                    pm_status.remove_command_indices.append(command_index)
                    if optimization_dict.get(pm_name) is None:
                        optimization_dict[pm_name] = OptimizationKinds()
                    optimization_dict[pm_name].need_remove_command = True

        # -------------------- Generating optimization strategies --------------------
        # ** Note: Don't generate duplicated strategies for a single instruction including multiple commands!
        insert_before_strategy = None
        add_cache_strategy = None
        remove_command_strategy = None

        for pm_name in optimization_dict.keys():
            pm_setting: PMSetting
            pm_status: PMHandler.PMStatus

            pm_setting = pm_settings[pm_name]
            pm_status = self.pm_statuses[pm_name]

            # Generate optimization strategies
            # --------------- Try to generate InsertBeforeStrategy ---------------
            # Note: additional_pre_commands are only added once in a stage!
            #   This means that multiple apt-get instructions will result in only once command addition
            if len(pm_setting.additional_pre_commands) > 0 and \
                    not pm_status.pre_commands_added:
                if insert_before_strategy is None:
                    insert_before_strategy = InsertBeforeStrategy(instruction_index, [])
                for additional_pre_command in pm_setting.additional_pre_commands:
                    if additional_pre_command not in insert_before_strategy.commands_insert:
                        insert_before_strategy.commands_insert.append(additional_pre_command)
                pm_status.pre_commands_added = True

            # --------------- Generate AddCacheStrategy ---------------
            if optimization_dict[pm_name].need_add_cache:
                if add_cache_strategy is None:
                    add_cache_strategy = AddCacheStrategy(instruction_index, [])
                for cache_dir in pm_status.cache_dirs:
                    if cache_dir not in add_cache_strategy.cache_dirs:
                        add_cache_strategy.cache_dirs.append(cache_dir)

            # --------------- Generate RemoveCommandStrategy ---------------
            if optimization_dict[pm_name].need_remove_command:
                if remove_command_strategy is None:
                    remove_command_strategy = RemoveCommandStrategy(instruction_index, [])
                for remove_command_index in pm_status.remove_command_indices:
                    remove_command_strategy.remove_command_indices.append(remove_command_index)

        if insert_before_strategy:
            self.optimization_strategies.append(insert_before_strategy)
        if add_cache_strategy:
            self.optimization_strategies.append(add_cache_strategy)
        if remove_command_strategy:
            self.optimization_strategies.append(remove_command_strategy)

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

