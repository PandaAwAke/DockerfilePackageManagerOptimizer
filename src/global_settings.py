class GlobalSettings(object):
    """
    The global settings for the running of the tool.

    -   pm_settings_path: The filepath of the settings of package managers.

    """

    def __init__(self, pm_settings_path='resources/PMSettings.yaml'):
        self.pm_settings_path = pm_settings_path


global_settings = GlobalSettings()
