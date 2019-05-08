# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import re

import pytest

from scout_apm.core.config import ScoutConfig, ScoutConfigNull


def test_get_config_value_from_env():
    os.environ["SCOUT_SOCKET_PATH"] = "/set/in/env"
    config = ScoutConfig()
    try:
        assert config.value("socket_path") == "/set/in/env"
    finally:
        del os.environ["SCOUT_SOCKET_PATH"]


def test_get_config_value_from_python():
    ScoutConfig.set(socket_path="/set/from/python")
    config = ScoutConfig()
    try:
        assert config.value("socket_path") == "/set/from/python"
    finally:
        ScoutConfig.reset_all()


def test_get_derived_config_value():
    ScoutConfig.set(core_agent_version="v1.1.8")
    config = ScoutConfig()
    try:
        assert re.match(
            r"/tmp/scout_apm_core/scout_apm_core"
            r"-v1\.1\.8"
            r"-(x86_64|i686|unknown)"
            r"-(unknown-linux-gnu|apple-darwin|unknown)"
            r"/core-agent\.sock",
            config.value("socket_path"),
        )
    finally:
        ScoutConfig.reset_all()


def test_override_triple():
    ScoutConfig.set(core_agent_triple="unknown-linux-musl")
    config = ScoutConfig()
    try:
        assert re.match(
            r"scout_apm_core-v.*-unknown-linux-musl",
            config.value("core_agent_full_name"),
        )
    finally:
        ScoutConfig.reset_all()


def test_get_default_config_value():
    config = ScoutConfig()
    assert config.value("core_agent_dir") == "/tmp/scout_apm_core"


def test_get_undefined_config_value():
    config = ScoutConfig()
    assert config.value("unknown value") is None


def test_env_outranks_python():
    os.environ["SCOUT_SOCKET_PATH"] = "/set/in/env"
    ScoutConfig.set(socket_path="/set/from/python")
    config = ScoutConfig()
    try:
        assert config.value("socket_path") == "/set/in/env"
    finally:
        del os.environ["SCOUT_SOCKET_PATH"]
        ScoutConfig.reset_all()


def test_log_config():
    # Include configs in various layers to exercise all code paths.
    os.environ["SCOUT_CORE_AGENT_DOWNLOAD"] = "False"
    ScoutConfig.set(core_agent_launch=False)
    config = ScoutConfig()
    try:
        # Logging the config doesn't crash.
        config.log()
    finally:
        del os.environ["SCOUT_CORE_AGENT_DOWNLOAD"]
        ScoutConfig.reset_all()


def test_core_agent_permissions_default():
    config = ScoutConfig()
    assert 0o700 == config.core_agent_permissions()


def test_core_agent_permissions_custom():
    ScoutConfig.set(core_agent_permissions=770)
    config = ScoutConfig()
    try:
        assert 0o770 == config.core_agent_permissions()
    finally:
        ScoutConfig.reset_all()


def test_core_agent_permissions_invalid_uses_default():
    ScoutConfig.set(core_agent_permissions="THIS IS INVALID")
    config = ScoutConfig()
    try:
        assert 0o700 == config.core_agent_permissions()
    finally:
        ScoutConfig.reset_all()


def test_null_config_name():
    # For coverage... this is never called elsewhere.
    ScoutConfigNull().name()


def test_boolean_conversion_from_env():
    os.environ["SCOUT_MONITOR"] = "True"
    config = ScoutConfig()
    try:
        assert config.value("monitor") is True
    finally:
        del os.environ["SCOUT_MONITOR"]


@pytest.mark.parametrize(
    "original, converted",
    [
        ("True", True),
        ("Yes", True),
        ("1", True),
        (True, True),
        ("False", False),
        ("No", False),
        ("0", False),
        (False, False),
        (object(), False),
    ],
)
def test_boolean_conversion_from_python(original, converted):
    ScoutConfig.set(monitor=original)
    config = ScoutConfig()
    try:
        assert config.value("monitor") is converted
    finally:
        ScoutConfig.reset_all()


def test_list_conversion_from_env():
    os.environ["SCOUT_DISABLED_INSTRUMENTS"] = "pymongo, redis"
    config = ScoutConfig()
    try:
        assert config.value("disabled_instruments") == ["pymongo", "redis"]
    finally:
        del os.environ["SCOUT_DISABLED_INSTRUMENTS"]


@pytest.mark.parametrize(
    "original, converted",
    [
        ("pymongo, redis", ["pymongo", "redis"]),
        (("pymongo", "redis"), ["pymongo", "redis"]),
        (["pymongo", "redis"], ["pymongo", "redis"]),
        ("", []),
        (object(), []),
    ],
)
def test_list_conversion_from_python(original, converted):
    ScoutConfig.set(disabled_instruments=original)
    config = ScoutConfig()
    try:
        assert config.value("disabled_instruments") == converted
    finally:
        ScoutConfig.reset_all()
