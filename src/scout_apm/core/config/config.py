from __future__ import absolute_import

import logging
import os
import platform

from scout_apm.core.git_revision import GitRevision

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
            ScoutConfigPython(),
            ScoutConfigDefaults(),
            ScoutConfigNull()]

    def value(self, key):
        value = self.locate_layer_for_key(key).value(key)
        if key in CONVERSIONS:
            converted_value = CONVERSIONS[key].convert(value)
        else:
            converted_value = value

        return converted_value

    def locate_layer_for_key(self, key):
        for layer in self.layers:
            if layer.has_config(key):
                return layer

    def log(self):
        logger.debug('Configuration Loaded:')
        for key in self.known_keys():
            layer = self.locate_layer_for_key(key)
            logger.debug('{:9}: {} = {}'.format(
                layer.name(),
                key,
                layer.value(key)))

    def known_keys(self):
        return [
            'application_root',
            'app_server',
            'core_agent_dir',
            'core_agent_download',
            'core_agent_launch',
            'core_agent_version',
            'disabled_instruments',
            'download_url',
            'framework',
            'framework_version',
            'revision_sha',
            'key',
            'hostname',
            'log_level',
            'name',
            'monitor',
            'socket_path'
        ]

    # scout_apm_core-latest-x86_64-apple-darwin.tgz
    def core_agent_full_name(self):
        return 'scout_apm_core-{version}-{arch}-{platform}'.format(
                version=self.value('core_agent_version'),
                arch=self.arch(),
                platform=self.platform())

    @classmethod
    def platform(cls):
        system_name = platform.system()
        if system_name == 'Linux':
            return 'unknown-linux-gnu'
        elif system_name == 'Darwin':
            return 'apple-darwin'
        else:
            return 'unknown'

    @classmethod
    def arch(cls):
        arch = platform.machine()
        if arch == 'i686':
            return 'i686'
        elif arch == 'x86_64':
            return 'x86_64'
        else:
            return 'unknown'

    @classmethod
    def set(cls, **kwargs):
        """
        Sets a configuration value for the Scout agent. Values set here will
        not override values set in ENV.
        """
        global SCOUT_PYTHON_VALUES
        for key, value in kwargs.items():
            SCOUT_PYTHON_VALUES[key] = value


# Module-level data, the ScoutConfig.set(key="value") adds to this
SCOUT_PYTHON_VALUES = {}


class ScoutConfigPython():
    """
    A configuration overlay that lets other parts of python set values.
    """
    def name(self):
        return 'Python'

    def has_config(self, key):
        return key in SCOUT_PYTHON_VALUES

    def value(self, key):
        return SCOUT_PYTHON_VALUES[key]


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
        self.core_agent_dir = '/tmp/scout_apm_core'
        self.core_agent_version = 'latest'
        self.defaults = {
                'application_root': '',
                'app_server': '',
                'core_agent_dir': self.core_agent_dir,
                'core_agent_download': True,
                'core_agent_launch': True,
                'core_agent_version': self.core_agent_version,
                'download_url': 'https://s3-us-west-1.amazonaws.com/scout-public-downloads/apm_core_agent/release',
                'framework': '',
                'framework_version': '',
                'revision_sha': GitRevision().detect(),
                'key': '',
                'hostname': '',
                'log_level': 'info',
                'name': '',
                'monitor': False,
                'disabled_instruments': [],
                'socket_path': '{}/scout_apm_core-{}-{}-{}/core-agent.sock'.format(self.core_agent_dir,
                                                                                   self.core_agent_version,
                                                                                   ScoutConfig.arch(),
                                                                                   ScoutConfig.platform())
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


class BooleanConversion():
    @classmethod
    def convert(cls, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('yes', 'true', 't', '1')
        # Unknown type - default to false?
        return False


class ListConversion():
    @classmethod
    def convert(cls, value):
        if isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        if isinstance(value, str):
            # Split on commas
            return value.split(',')
        # Unknown type - default to empty?
        return []

CONVERSIONS = {
    'core_agent_download': BooleanConversion,
    'core_agent_launch': BooleanConversion,
    'monitor': BooleanConversion,
    'disabled_instruments': ListConversion,
}
