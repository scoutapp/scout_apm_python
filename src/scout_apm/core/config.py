from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import os
import sys

from scout_apm.core.git_revision import GitRevision
from scout_apm.core.platform_detection import PlatformDetection
from scout_apm.core.util import octal

logger = logging.getLogger(__name__)


class ScoutConfig(object):
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
            ScoutConfigDerived(self),
            ScoutConfigDefaults(),
            ScoutConfigNull(),
        ]

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
        else:  # pragma: no cover
            # Not reachable because ScoutConfigNull returns None for all keys.
            assert False, "key not found in any layer"

    def log(self):
        logger.debug("Configuration Loaded:")
        for key in self.known_keys():
            layer = self.locate_layer_for_key(key)
            logger.debug("%-9s: %s = %s", layer.name(), key, layer.value(key))

    def known_keys(self):
        return [
            "app_server",
            "application_root",
            "core_agent_dir",
            "core_agent_download",
            "core_agent_launch",
            "core_agent_permissions",
            "core_agent_version",
            "disabled_instruments",
            "download_url",
            "framework",
            "framework_version",
            "hostname",
            "ignore",
            "key",
            "log_level",
            "monitor",
            "name",
            "revision_sha",
            "scm_subdirectory",
            "socket_path",
        ]

    def core_agent_permissions(self):
        try:
            return octal(self.value("core_agent_permissions"))
        except ValueError as e:
            logger.error(
                "Invalid core_agent_permissions value: %s." " Using default: %s",
                repr(e),
                0o700,
            )
            return 0o700

    @classmethod
    def set(cls, **kwargs):
        """
        Sets a configuration value for the Scout agent. Values set here will
        not override values set in ENV.
        """
        global SCOUT_PYTHON_VALUES
        for key, value in kwargs.items():
            SCOUT_PYTHON_VALUES[key] = value

    @classmethod
    def reset_all(cls):
        """
        Remove all configuration settings set via `ScoutConfig.set(...)`.

        This is meant for use in testing.
        """
        global SCOUT_PYTHON_VALUES
        SCOUT_PYTHON_VALUES.clear()


# Module-level data, the ScoutConfig.set(key="value") adds to this
SCOUT_PYTHON_VALUES = {}


class ScoutConfigPython(object):
    """
    A configuration overlay that lets other parts of python set values.
    """

    def name(self):
        return "Python"

    def has_config(self, key):
        return key in SCOUT_PYTHON_VALUES

    def value(self, key):
        return SCOUT_PYTHON_VALUES[key]


class ScoutConfigEnv(object):
    """
    Reads configuration from environment by prefixing the key
    requested with "SCOUT_"

    Example: the `log_level` config looks for SCOUT_LOG_LEVEL
    environment variable
    """

    def name(self):
        return "ENV"

    def has_config(self, key):
        env_key = self.modify_key(key)
        return env_key in os.environ

    def value(self, key):
        env_key = self.modify_key(key)
        return os.environ[env_key]

    def modify_key(self, key):
        env_key = ("SCOUT_" + key).upper()
        return env_key


class ScoutConfigDerived(object):
    """
    A configuration overlay that calculates from other values.
    """

    def __init__(self, config):
        """
        config argument is the overall ScoutConfig var, so we can lookup the
        components of the derived info.
        """
        self.config = config

    def name(self):
        return "Derived"

    def has_config(self, key):
        return self.lookup_func(key) is not None

    def value(self, key):
        return self.lookup_func(key)()

    def lookup_func(self, key):
        """
        Returns the derive_#{key} function, or None if it isn't defined
        """
        func_name = "derive_" + key
        return getattr(self, func_name, None)

    def derive_socket_path(self):
        return "{}/{}/core-agent.sock".format(
            self.config.value("core_agent_dir"),
            self.config.value("core_agent_full_name"),
        )

    def derive_core_agent_full_name(self):
        return "{name}-{version}-{triple}".format(
            name="scout_apm_core",
            version=self.config.value("core_agent_version"),
            triple=self.config.value("core_agent_triple"),
        )

    def derive_core_agent_triple(self):
        return PlatformDetection.get_triple()


class ScoutConfigDefaults(object):
    """
    Provides default values for important configurations
    """

    def name(self):
        return "Defaults"

    def __init__(self):
        self.defaults = {
            "app_server": "",
            "application_root": "",
            "core_agent_dir": "/tmp/scout_apm_core",
            "core_agent_download": True,
            "core_agent_launch": True,
            "core_agent_permissions": 700,
            "core_agent_version": "v1.1.8",  # can be an exact tag name, or 'latest'
            "disabled_instruments": [],
            "download_url": "https://s3-us-west-1.amazonaws.com/scout-public-downloads/apm_core_agent/release",  # noqa: E501
            "framework": "",
            "framework_version": "",
            "hostname": "",
            "key": "",
            "log_level": "info",
            "monitor": False,
            "name": "",
            "revision_sha": GitRevision().detect(),
            "scm_subdirectory": "",
        }

    def has_config(self, key):
        return key in self.defaults

    def value(self, key):
        return self.defaults[key]


# Always returns None to any key
class ScoutConfigNull(object):
    """
    Always answers that a key is present, but the value is None

    Used as the last step of the layered configuration.
    """

    def name(self):
        return "Null"

    def has_config(self, key):
        return True

    def value(self, key):
        return None


string_type = str if sys.version_info[0] >= 3 else basestring  # noqa: F821


class BooleanConversion(object):
    @classmethod
    def convert(cls, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, string_type):
            return value.lower() in ("yes", "true", "t", "1")
        # Unknown type - default to false?
        return False


class ListConversion(object):
    @classmethod
    def convert(cls, value):
        if isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        if isinstance(value, string_type):
            # Split on commas
            return [item.strip() for item in value.split(",") if item]
        # Unknown type - default to empty?
        return []


CONVERSIONS = {
    "core_agent_download": BooleanConversion,
    "core_agent_launch": BooleanConversion,
    "monitor": BooleanConversion,
    "disabled_instruments": ListConversion,
    "ignore": ListConversion,
}
