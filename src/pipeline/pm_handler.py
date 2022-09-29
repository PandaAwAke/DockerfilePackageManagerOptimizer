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
                    cache_dirs=[context_util.replace_home_char(cache_dir, self.global_status)
                                for cache_dir in pm_settings[pm_name].default_cache_dirs]
                )

            # Concatenate the command words as string to match the regexes.
            pm_command_str = str_util.join_command_words(command[1:])

            pm_setting: PMSetting
            pm_status: PMHandler.PMStatus

            pm_setting = pm_settings[pm_name]
            pm_status = self.pm_statuses[pm_name]

            # ------------------------ Regex matching ------------------------
            # Case for modifying the cache dir
            for command_regex_modify_cache_dir in pm_setting.commands_regex_modify_cache_dir:
                modify_cache_dir_re = re.compile(command_regex_modify_cache_dir)
                match_result = modify_cache_dir_re.match(pm_command_str)
                # Only considering one match! So we will return directly once finished handling the match.
                if match_result and len(match_result.groups()) > 0:  # This command will modify the cache dir
                    pm_status.cache_dirs = []
                    for new_cache_dir in match_result.groups():
                        new_cache_dir = context_util.replace_home_char(new_cache_dir, self.global_status).strip()
                        new_cache_dir = context_util.get_absolute_path(new_cache_dir, self.global_status)
                        pm_status.cache_dirs.append(new_cache_dir)
                    return
                # TODO: Consider more conditions for modifying cache dir

            # Case for running the package manager's build/install process
            for command_regex_run in pm_setting.commands_regex_run:
                run_re = re.compile(command_regex_run)
                match_result = run_re.match(pm_command_str)
                # Only considering one match
                if match_result:
                    if optimization_dict.get(pm_name) is None:
                        optimization_dict[pm_name] = OptimizationKinds()
                    optimization_dict[pm_name].need_add_cache = True

            # Case for removing anti-cache commands: in RunHandler

        # -------------------- Generating optimization strategies --------------------
        # ** Note: Don't generate duplicated strategies for a single instruction including multiple commands!
        insert_before_strategy = None
        add_cache_strategy = None

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

        if insert_before_strategy:
            self.optimization_strategies.append(insert_before_strategy)
        if add_cache_strategy:
            self.optimization_strategies.append(add_cache_strategy)

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

