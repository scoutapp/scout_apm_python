from __future__ import absolute_import

import logging
import os

logger = logging.getLogger(__name__)


class ScoutConfig():
    """
    Configuration object for the ScoutApm agent.

    Contains a list of configuration "layers". When a configuration key is
    looked up, each layer is asked in turn if it knows the value. The first one
    to answer affirmatively returns the value.
    """
    def __init__(self):
        self.layers = [
            ScoutConfigEnv(),
            ScoutConfigDefaults(),
            ScoutConfigNull()]

        logger.info('Configuration Loaded:')
        self.log()

    def value(self, key):
        return self.locate_layer_for_key(key).value(key)

    def locate_layer_for_key(self, key):
        for layer in self.layers:
            if layer.has_config(key):
                return layer

    def log(self):
        for key in self.known_keys():
            layer = self.locate_layer_for_key(key)
            logger.info('{:9}: {} = {}'.format(
                layer.name(),
                key,
                layer.value(key)))

    def known_keys(self):
        return [
            'socket_path',
            'download_url',
            'download_version',
            'log_level',
            'name',
            'key',
            'manual_daemon',
        ]


class ScoutConfigEnv():
    """
    Reads configuration from environment by prefixing the key
    requested with "SCOUT_"

    Example: the `log_level` config looks for SCOUT_LOG_LEVEL
    environment variable
    """

    def name(self):
        return 'ENV'

    def has_config(self, key):
        env_key = self.modify_key(key)
        return env_key in os.environ

    def value(self, key):
        env_key = self.modify_key(key)
        return os.environ[env_key]

    def modify_key(self, key):
        env_key = ('SCOUT_' + key).upper()
        return env_key


class ScoutConfigDefaults():
    """
    Provides default values for important configurations
    """

    def name(self):
        return 'Defaults'

    def __init__(self):
        self.defaults = {
                'download_url': 'https://downloads.scoutapp.com',
                'download_version': 'latest',
                'key': 'Qnk5SKpNEeboPdeJkhae',
                'log_level': 'info',
                'name': 'CoreAgent',
                'socket_path': '/tmp/scout_core_agent',
        }

    def has_config(self, key):
        return key in self.defaults

    def value(self, key):
        return self.defaults[key]


# Always returns None to any key
class ScoutConfigNull():
    """
    Always answers that a key is present, but the value is None

    Used as the last step of the layered configuration.
    """

    def name(self):
        return 'Null'

    def has_config(self, key):
        return True

    def value(self, key):
        return None
