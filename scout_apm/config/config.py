import os

class ScoutConfig():
    def __init__(self):
        self.layers = [ScoutConfigEnv(), ScoutConfigFile(), ScoutConfigDefaults(), ScoutConfigNull()]
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
    def __init__(self):
        print('ScoutConfigFile')

    def has_key(self, key):
        return None

    def value(self, key):
        raise 'Omg dont use this.'


class ScoutConfigDefaults():
    def __init__(self):
        print('ScoutConfigDefaults')
        self.defaults = {
                'core_agent_socket': '/tmp/core_agent_socket'
                }

    def has_key(self, key):
        return key in self.defaults

    def value(self, key):
        return self.defaults[key]


# Always returns None to any key
class ScoutConfigNull():
    def __init__(self):
        print("ScoutConfigNull")

    def has_key(self, key):
        return True

    def value(self, key):
        return None
