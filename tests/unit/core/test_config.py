# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import re
import sys

import pytest

from scout_apm.core.config import Null, ScoutConfig, scout_config
from tests.compat import mock


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


def test_unset_config_value_from_python():
    ScoutConfig.set(revision_sha="foobar")
    ScoutConfig.unset("revision_sha")
    assert ScoutConfig().value("revision_sha") == ""  # from defaults


def test_get_derived_config_value():
    ScoutConfig.set(core_agent_version="v1.1.8")
    config = ScoutConfig()
    try:
        assert re.match(
            r"/tmp/scout_apm_core/scout_apm_core"
            r"-v1\.1\.8"
            r"-(x86_64|i686|unknown)"
            r"-(unknown-linux-gnu|apple-darwin|unknown)"
            r"/scout-agent\.sock",
            config.value("core_agent_socket_path"),
        )
    finally:
        ScoutConfig.reset_all()


def test_override_triple(caplog):
    triple = "unknown-unknown-linux-musl"
    ScoutConfig.set(core_agent_triple=triple)
    config = ScoutConfig()
    try:
        full_name = config.value("core_agent_full_name")
    finally:
        ScoutConfig.reset_all()

    assert full_name.endswith(triple)
    assert caplog.record_tuples == []


def test_override_triple_invalid(recwarn):
    bad_triple = "badtriple"
    ScoutConfig.set(core_agent_triple=bad_triple)
    config = ScoutConfig()
    try:
        full_name = config.value("core_agent_full_name")
    finally:
        ScoutConfig.reset_all()

    assert full_name.endswith(bad_triple)
    assert len(recwarn) == 1
    warning = recwarn.pop(Warning)
    assert str(warning.message) == "Invalid value for core_agent_triple: badtriple"


def test_get_default_config_value():
    config = ScoutConfig()
    assert config.value("core_agent_dir") == "/tmp/scout_apm_core"


def test_get_undefined_config_value():
    config = ScoutConfig()
    assert config.value("unknown value") is None


def test_get_undefined_config_value_null_layer_removed():
    # For coverage
    config = ScoutConfig()
    config.layers = [x for x in config.layers if not isinstance(x, Null)]

    with pytest.raises(ValueError) as excinfo:
        config.value("unknown value")

    assert isinstance(excinfo.value, ValueError)
    if sys.version_info[0] == 2:
        expected_msg = "key u'unknown value' not found in any layer"
    else:
        expected_msg = "key 'unknown value' not found in any layer"
    assert excinfo.value.args == (expected_msg,)


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
    assert scout_config.core_agent_permissions() == 0o700


def test_core_agent_permissions_custom_int():
    scout_config.set(core_agent_permissions=770)
    try:
        assert scout_config.core_agent_permissions() == 0o770
    finally:
        ScoutConfig.reset_all()


def test_core_agent_permissions_custom_str():
    scout_config.set(core_agent_permissions="770")
    try:
        assert scout_config.core_agent_permissions() == 0o770
    finally:
        ScoutConfig.reset_all()


def test_core_agent_permissions_invalid_uses_default():
    scout_config.set(core_agent_permissions="THIS IS INVALID")
    try:
        assert scout_config.core_agent_permissions() == 0o700
    finally:
        ScoutConfig.reset_all()


def test_boolean_conversion_from_env():
    config = ScoutConfig()
    with mock.patch.dict(os.environ, {"SCOUT_MONITOR": "True"}):
        assert config.value("monitor") is True


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


def test_float_conversion_from_env():
    config = ScoutConfig()
    with mock.patch.dict(os.environ, {"SCOUT_SHUTDOWN_TIMEOUT_SECONDS": "0"}):
        value = config.value("shutdown_timeout_seconds")
    assert isinstance(value, float)
    assert value == 0.0


@pytest.mark.parametrize(
    "original, converted", [("0", 0.0), ("2", 2.0), ("x", 0.0)],
)
def test_float_conversion_from_python(original, converted):
    ScoutConfig.set(shutdown_timeout_seconds=original)
    config = ScoutConfig()
    try:
        assert config.value("shutdown_timeout_seconds") == converted
    finally:
        ScoutConfig.reset_all()


def test_list_conversion_from_env():
    config = ScoutConfig()
    with mock.patch.dict(os.environ, {"SCOUT_DISABLED_INSTRUMENTS": "pymongo, redis"}):
        assert config.value("disabled_instruments") == ["pymongo", "redis"]


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


@pytest.mark.parametrize(
    "environ,expected",
    [
        ({}, ""),
        ({"HEROKU_SLUG_COMMIT": "FROM_HEROKU"}, "FROM_HEROKU"),
        ({"SCOUT_REVISION_SHA": "FROM_SCOUT"}, "FROM_SCOUT"),
        (
            {"HEROKU_SLUG_COMMIT": "FROM_HEROKU", "SCOUT_REVISION_SHA": "FROM_SCOUT"},
            "FROM_SCOUT",
        ),
        ({"HEROKU_SLUG_COMMIT": "", "SCOUT_REVISION_SHA": ""}, ""),
    ],
)
def test_revision_sha(environ, expected):
    with mock.patch.dict(os.environ, clear=True, **environ):
        assert ScoutConfig().value("revision_sha") == expected
