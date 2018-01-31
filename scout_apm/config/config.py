import os
from .yaml_file import YamlFile


class ScoutConfig():
    def __init__(self, config_file=None):
        # We have to ask the ENV configuration for where the config file even
        # *is*, so allow this to be created with or without a file
        if config_file is None:
            self.layers = [ScoutConfigEnv(), ScoutConfigDefaults(), ScoutConfigNull()]
        else:
            self.layers = [
                ScoutConfigEnv(),
                ScoutConfigFile(config_file),
                ScoutConfigDefaults(),
                ScoutConfigNull()]

        print('Init ScoutConfig')

    def value(self, key):
        for layer in self.layers:
            if layer.has_key(key):
                return layer.value(key)


class ScoutConfigEnv():
    def has_key(self, key):
        env_key = self.modify_key(key)
        return env_key in os.environ

    def value(self, key):
        env_key = self.modify_key(key)
        return os.environ[env_key]

    def modify_key(self, key):
        env_key = ('SCOUT_' + key).upper()
        return env_key


class ScoutConfigFile():
    def __init__(self, config_file='scout_apm.yml'):
        self.data = YamlFile(config_file).parse()

    def has_key(self, key):
        return key in self.data

    def value(self, key):
        return self.data[key]


class ScoutConfigDefaults():
    def __init__(self):
        self.defaults = {
                'core_agent_socket': '/tmp/scout_core_agent',
                'download_url': 'https://downloads.scoutapp.com',
        }

    def has_key(self, key):
        return key in self.defaults

    def value(self, key):
        return self.defaults[key]


# Always returns None to any key
class ScoutConfigNull():
    def has_key(self, key):
        return True

    def value(self, key):
        return None
