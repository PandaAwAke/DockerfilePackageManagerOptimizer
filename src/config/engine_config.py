import logging


class GlobalSettings(object):
    """
    The global settings for the running of the tool.

    -   pm_settings_path: The filepath of the settings of package managers.

    """

    def __init__(self, pm_settings_path='resources/settings.yaml'):
        self.pm_settings_path = pm_settings_path


class EngineSettings(object):
    """
    The settings of the engine.
    """

    def __init__(self):
        self.input_file = None
        self.output_file = None
        self.suffix = '.optimized'
        self.show_stats = False
        self.fail_file = './DPMO_failures.txt'
        self.fail_fileobj = None
        self.remove_command_with_true = True
        self.logging_level = logging.INFO


global_settings = GlobalSettings()
engine_settings = EngineSettings()

