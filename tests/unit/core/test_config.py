# coding=utf-8

import logging
import os
import pprint

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


def test_log_config(caplog):
    # Include configs in various layers to exercise all code paths.
    os.environ["SCOUT_CORE_AGENT_DOWNLOAD"] = "False"
    ScoutConfig.set(core_agent_launch=False, key="abcdefghij")
    config = ScoutConfig()
    try:
        # Logging the config doesn't crash.
        config.log()
    finally:
        del os.environ["SCOUT_CORE_AGENT_DOWNLOAD"]
        ScoutConfig.reset_all()

    assert caplog.record_tuples[0] == (
        "scout_apm.core.config",
        logging.DEBUG,
        "Configuration Loaded:",
    )
    assert (
        "scout_apm.core.config",
        logging.DEBUG,
        "Python   : core_agent_launch = False",
    ) in caplog.record_tuples
    assert "abcdefghij" not in pprint.pformat(caplog.record_tuples)


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
    "original, converted",
    [("0", 0.0), ("2", 2.0), ("x", 0.0)],
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


def test_sample_rate_conversion_from_env():
    config = ScoutConfig()
    with mock.patch.dict(os.environ, {"SCOUT_SAMPLE_RATE": "50"}):
        value = config.value("sample_rate")
    assert isinstance(value, float)
    assert value == 0.50  # 50 is converted to 0.50 for backwards compatibility


@pytest.mark.parametrize(
    "original, converted",
    [
        # Float values (0-1 range)
        ("0", 0.0),
        ("0.5", 0.5),
        ("1", 1.0),
        ("0.001", 0.001),
        # Integer percentages (> 1, backwards compatibility)
        ("50", 0.50),
        ("100", 1.0),
        ("1", 1.0),
        ("1.5", 0.015),  # 1.5% -> 0.015
        # Edge cases
        ("x", 1.0),  # Invalid defaults to 1.0
        (None, None),  # None is preserved
        # Clamping
        ("-2.5", 0.0),  # Negative values clamped to 0
        ("150", 1.0),  # > 100% clamped to 1.0
    ],
)
def test_sample_rate_conversion_from_python(original, converted):
    ScoutConfig.set(sample_rate=original)
    config = ScoutConfig()
    try:
        assert config.value("sample_rate") == converted
    finally:
        ScoutConfig.reset_all()


def test_endpoint_sampling_conversion_from_env():
    config = ScoutConfig()
    with mock.patch.dict(
        os.environ, {"SCOUT_SAMPLE_ENDPOINTS": " /endpoint:40,/test:0"}
    ):
        value = config.value("sample_endpoints")
    assert isinstance(value, dict)
    assert value == {"endpoint": 0.40, "test": 0.0}  # Converted to floats


@pytest.mark.parametrize(
    "original, converted",
    [
        # String format with percentages (backwards compat)
        ("/endpoint:40,/test:0", {"endpoint": 0.40, "test": 0.0}),
        # Dict format with percentages (backwards compat)
        ({"endpoint": 40, "test": 0}, {"endpoint": 0.40, "test": 0.0}),
        # Dict format with floats
        ({"endpoint": 0.40, "test": 0.0}, {"endpoint": 0.40, "test": 0.0}),
        # String format with floats
        ("/endpoint:0.5,/test:0.001", {"endpoint": 0.5, "test": 0.001}),
        # Empty
        ("", {}),
        (object(), {}),
    ],
)
def test_endpoint_sampling_conversion_from_python(original, converted):
    ScoutConfig.set(sample_endpoints=original)
    config = ScoutConfig()
    try:
        assert config.value("sample_endpoints") == converted
    finally:
        ScoutConfig.reset_all()


def test_job_sampling_conversion_from_env():
    config = ScoutConfig()
    with mock.patch.dict(os.environ, {"SCOUT_SAMPLE_JOBS": "job1:30,job2:70"}):
        value = config.value("sample_jobs")
    assert isinstance(value, dict)
    assert value == {"job1": 0.30, "job2": 0.70}  # Converted to floats


@pytest.mark.parametrize(
    "original, converted",
    [
        # String format with percentages (backwards compat)
        ("job1:30,job2:70", {"job1": 0.30, "job2": 0.70}),
        # Dict format with percentages (backwards compat)
        ({"job1": 30, "job2": 70}, {"job1": 0.30, "job2": 0.70}),
        # Dict format with floats
        ({"job1": 0.30, "job2": 0.70}, {"job1": 0.30, "job2": 0.70}),
        # String format with floats
        ("job1:0.5,job2:0.001", {"job1": 0.5, "job2": 0.001}),
        # Empty
        ("", {}),
        (object(), {}),
    ],
)
def test_job_sampling_conversion_from_python(original, converted):
    ScoutConfig.set(sample_jobs=original)
    config = ScoutConfig()
    try:
        assert config.value("sample_jobs") == converted
    finally:
        ScoutConfig.reset_all()


# Additional tests for nullable sample rates
@pytest.mark.parametrize(
    "original, converted",
    [
        (None, None),
        ("0", 0.0),
        ("0.5", 0.5),
        ("50", 0.50),
        ("100", 1.0),
    ],
)
def test_endpoint_sample_rate_nullable(original, converted):
    """Test that endpoint_sample_rate allows None and converts other values."""
    ScoutConfig.set(endpoint_sample_rate=original)
    config = ScoutConfig()
    try:
        assert config.value("endpoint_sample_rate") == converted
    finally:
        ScoutConfig.reset_all()


@pytest.mark.parametrize(
    "original, converted",
    [
        (None, None),
        ("0", 0.0),
        ("0.5", 0.5),
        ("50", 0.50),
        ("100", 1.0),
    ],
)
def test_job_sample_rate_nullable(original, converted):
    """Test that job_sample_rate allows None and converts other values."""
    ScoutConfig.set(job_sample_rate=original)
    config = ScoutConfig()
    try:
        assert config.value("job_sample_rate") == converted
    finally:
        ScoutConfig.reset_all()
