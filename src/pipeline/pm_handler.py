import re

from config.optimization_config import *
from model.global_status import GlobalStatus
from model.optimization_strategy import *
from util import context_util, str_util


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

    def __init__(self, global_status: GlobalStatus, optimization_strategies):
        """
        Initialize the PMHandler.

        :param global_status: the global_status of this stage created by stage simulator.
        """
        self.global_status = global_status
        self.pm_statuses = {}   # Key: PM's name; Value: PMStatus object
        self.optimization_strategies = optimization_strategies

    def handle(self, command_index: int, command: list, instruction_index: int):
        """
        Handle a list of commands from RunHandler.

        :param command_index: the PM-related command index inside this instruction.
        :param command: the PM-related command inside this instruction.
        :param instruction_index: the index of this instruction.
        :return: None
        """

        add_cache = False

        # -------------------- Handling PM-related commands --------------------
        assert len(command) > 0     # Ensured by run_handler.handle()
        executable = command[0].s
        pm_name = self._get_executable_package_manager(executable)

        # If firstly encountered this PM, create a PMStatus
        if pm_name not in self.pm_statuses.keys():
            self.pm_statuses[pm_name] = PMHandler.PMStatus(cache_dirs=[])

        # Concatenate the command words as string to match the regexes.
        pm_command_str = str_util.join_command_words(command[1:])

        pm_setting: PMSetting = pm_settings[pm_name]    # Initialized by config.optimization_config
        pm_status: PMHandler.PMStatus = self.pm_statuses[pm_name]

        # ------------------------ Regex matching ------------------------
        # Case for modifying the cache dir
        for command_regex_modify_cache_dir in pm_setting.commands_regex_modify_cache_dir:
            modify_cache_dir_re = re.compile(command_regex_modify_cache_dir)
            match_result = modify_cache_dir_re.match(pm_command_str)
            # Only considering one match! So we will return directly once finished handling the match.
            if match_result and len(match_result.groups()) > 0:  # This command will modify the cache dir
                pm_status.cache_dirs = []
                for new_cache_dir in match_result.groups():
                    new_cache_dir = str_util.strip_and_dequote(new_cache_dir)
                    new_cache_dir = context_util.replace_home_char(new_cache_dir, self.global_status).strip()
                    new_cache_dir = context_util.get_absolute_path(new_cache_dir, self.global_status)
                    pm_status.cache_dirs.append(new_cache_dir)
            # TODO: Consider more conditions for modifying cache dir

        # Case for running the package manager's build/install process
        for command_regex_run in pm_setting.commands_regex_run:
            run_re = re.compile(command_regex_run)
            match_result = run_re.match(pm_command_str)
            # Only considering one match
            if match_result:
                add_cache = True
                break

        # --------------- Try to generate RemoveOptionStrategy ---------------
        # Case for removing anti-cache options
        remove_options = []
        for anti_cache_option in pm_setting.anti_cache_options:
            for word in command:
                if word.s.strip() == anti_cache_option and anti_cache_option not in remove_options:
                    remove_options.append(anti_cache_option)
        if len(remove_options) > 0:
            self.optimization_strategies.append(RemoveOptionStrategy(
                instruction_index=instruction_index,
                command_index=command_index,
                remove_options=remove_options
            ))

        # --------------- Try to generate InsertBeforeStrategy ---------------
        # Note: additional_pre_commands are only added once in a stage!
        #   This means that multiple apt-get instructions will result in only once command addition
        if len(pm_setting.additional_pre_commands) > 0 and not pm_status.pre_commands_added:
            insert_before_strategy = InsertBeforeStrategy(instruction_index, [])
            for additional_pre_command in pm_setting.additional_pre_commands:
                if additional_pre_command not in insert_before_strategy.commands_insert:
                    insert_before_strategy.commands_insert.append(additional_pre_command)
            self.optimization_strategies.append(insert_before_strategy)
            pm_status.pre_commands_added = True

        # -------------------- Try to generate AddCacheStrategy --------------------
        if add_cache:
            # ** Note: Don't generate duplicated strategies for a single instruction including multiple commands!
            add_cache_strategy = None
            for strategy in self.optimization_strategies:
                if isinstance(strategy, AddCacheStrategy) and strategy.instruction_index == instruction_index:
                    add_cache_strategy = strategy
                    break

            if add_cache_strategy is None:
                add_cache_strategy = AddCacheStrategy(instruction_index, [])
                self.optimization_strategies.append(add_cache_strategy)

            cache_dirs = pm_status.cache_dirs
            if len(cache_dirs) == 0:
                cache_dirs = [
                    context_util.replace_home_char(cache_dir, self.global_status)
                    for cache_dir in pm_settings[pm_name].default_cache_dirs
                ]

            for cache_dir in cache_dirs:
                if cache_dir not in add_cache_strategy.cache_dirs:
                    add_cache_strategy.cache_dirs.append(cache_dir)

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

