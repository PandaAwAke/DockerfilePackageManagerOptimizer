import logging

import yaml
import sys

from config.engine_config import global_settings


class PMSetting(object):
    """
    The settings for a package manager, read from "settings.yaml".
    """

    def __init__(self, executables: list,
                 commands_regex_run: list,
                 default_cache_dirs: list,
                 commands_regex_modify_cache_dir: list = None,
                 additional_pre_commands: list = None,
                 anti_cache_options: list = None):
        """
        Initialize the PM's settings.

        :param executables: the executables of this PM, for example: [apt, apt-get, ...] for apt.
        :param commands_regex_run: the regular expressions for running the PM download/install/compile commands.
        :param default_cache_dirs: the default download cache directories for this PM
                ("~" inside the filepath is also supported and recommended).
        :param commands_regex_modify_cache_dir: (Nullable) the regular expressions for modifying the
                PM cache directories commands. Group 1 of the regex is the new filepath.
        :param additional_pre_commands: (Nullable) the commands need to be added before all this PM related commands.
        :param anti_cache_options: (Nullable) the anti-cache options need to be removed in PM related commands.
        """
        self.executables = executables
        self.commands_regex_run = commands_regex_run
        self.default_cache_dirs = default_cache_dirs
        self.commands_regex_modify_cache_dir = commands_regex_modify_cache_dir
        self.additional_pre_commands = additional_pre_commands
        self.anti_cache_options = anti_cache_options


class GlobalOptimizationSettings(object):
    """
    The settings for global optimization, read from "settings.yaml".
    """

    def __init__(self, anti_cache_commands_regex=None):
        """
        Initialize the global optimization settings.
        :param anti_cache_commands_regex: (Nullable) the regular expressions for anti-cache commands.
                This will be used to recognize and remove anti-cache commands when optimizing.
        """
        if anti_cache_commands_regex is None:
            anti_cache_commands_regex = []
        self.anti_cache_commands_regex = anti_cache_commands_regex


def load_optimization_settings():
    """
    Load all PM settings from "settings.yaml" into pm_settings and global_opt_settings.

    :return: None
    """
    if len(pm_settings) > 0:
        return
    try:
        f = open(file=global_settings.pm_settings_path, mode='r', encoding='utf-8')
        pm_yaml_settings = yaml.safe_load(f)
    except Exception as e:  # Including: IOError, yaml.YAMLError
        logging.error(e)
        sys.exit(-1)

    global global_opt_settings
    global_opt_settings = GlobalOptimizationSettings()
    global_opt_settings.anti_cache_commands_regex = pm_yaml_settings['anti-cache-commands-regex']

    pm_yaml_settings: dict = pm_yaml_settings['packageManagers']
    for pm_name in pm_yaml_settings.keys():
        pm_yaml_dict: dict = pm_yaml_settings[pm_name]

        pm_setting = PMSetting(
            executables=pm_yaml_dict.get('executables') or [pm_name],
            commands_regex_run=pm_yaml_dict.get('commands-regex-run') or [],
            default_cache_dirs=pm_yaml_dict.get('default-cache-dirs') or [],
            commands_regex_modify_cache_dir=pm_yaml_dict.get('commands-regex-modify-cache-dir') or [],
            additional_pre_commands=pm_yaml_dict.get('additional-pre-commands') or [],
            anti_cache_options=pm_yaml_dict.get('anti-cache-options') or [],
        )

        if len(pm_setting.commands_regex_run) == 0:
            logging.error('commands-regex-run is not set for "{0}"!'.format(pm_name))
            sys.exit(-1)
        if len(pm_setting.default_cache_dirs) == 0:
            logging.error('default-cache-dirs is not set for "{0}"!'.format(pm_name))
            sys.exit(-1)
        pm_settings[pm_name] = pm_setting
    f.close()


pm_settings = {}    # All PM's settings. Key: PM's name; Value: a PMSetting object.
global_opt_settings: GlobalOptimizationSettings

