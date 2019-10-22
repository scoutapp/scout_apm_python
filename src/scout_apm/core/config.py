# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import os

from scout_apm.compat import string_type
from scout_apm.core import platform_detection
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
            return CONVERSIONS[key](value)
        return value

    def locate_layer_for_key(self, key):
        for layer in self.layers:
            if layer.has_config(key):
                return layer

        # Should be unreachable because ScoutConfigNull returns None for all
        # keys.
        raise ValueError("key {!r} not found in any layer".format(key))

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
            "core_agent_log_level",
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
        except ValueError:
            logger.exception(
                "Invalid core_agent_permissions value, using default of 0o700"
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
    def unset(cls, *keys):
        """
        Removes a configuration value for the Scout agent.
        """
        global SCOUT_PYTHON_VALUES
        for key in keys:
            SCOUT_PYTHON_VALUES.pop(key, None)

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

    Example: the `key` config looks for SCOUT_KEY
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
        return "{}/{}/scout-agent.sock".format(
            self.config.value("core_agent_dir"),
            self.config.value("core_agent_full_name"),
        )

    def derive_core_agent_full_name(self):
        triple = self.config.value("core_agent_triple")
        if not platform_detection.is_valid_triple(triple):
            logger.warning("Invalid value for core_agent_triple: %s", triple)
        return "{name}-{version}-{triple}".format(
            name="scout_apm_core",
            version=self.config.value("core_agent_version"),
            triple=triple,
        )

    def derive_core_agent_triple(self):
        return platform_detection.get_triple()


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
            "core_agent_log_level": "info",
            "core_agent_permissions": 700,
            "core_agent_version": "v1.2.4",  # can be an exact tag name, or 'latest'
            "disabled_instruments": [],
            "download_url": "https://s3-us-west-1.amazonaws.com/scout-public-downloads/apm_core_agent/release",  # noqa: E501
            "framework": "",
            "framework_version": "",
            "hostname": None,
            "key": "",
            "monitor": False,
            "name": "",
            "revision_sha": self._git_revision_sha(),
            "scm_subdirectory": "",
            "uri_reporting": "filtered_params",
        }

    def _git_revision_sha(self):
        # N.B. The environment variable SCOUT_REVISION_SHA may also be used,
        # but that will be picked up by ScoutConfigEnv
        return os.environ.get("HEROKU_SLUG_COMMIT", "")

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


def convert_to_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, string_type):
        return value.lower() in ("yes", "true", "t", "1")
    # Unknown type - default to false?
    return False


def convert_to_list(value):
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
    "core_agent_download": convert_to_bool,
    "core_agent_launch": convert_to_bool,
    "monitor": convert_to_bool,
    "disabled_instruments": convert_to_list,
    "ignore": convert_to_list,
}
