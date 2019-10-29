# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import subprocess
import time

import pytest

from scout_apm.core.config import ScoutConfig
from scout_apm.core.context import AgentContext
from scout_apm.core.core_agent_manager import CoreAgentManager
from tests.compat import mock


@pytest.fixture
def core_agent_manager(core_agent_dir):
    # Shorten path to socket to prevent core-agent from failing with:
    #   Error opening listener on socket: Custom { kind: InvalidInput,
    #   error: StringError("path must be shorter than SUN_LEN") }
    socket_path = "{}/test.sock".format(core_agent_dir)
    ScoutConfig.set(core_agent_dir=core_agent_dir, socket_path=socket_path)
    AgentContext.build()
    core_agent_manager = CoreAgentManager()
    try:
        yield core_agent_manager
    finally:
        assert not is_running(core_agent_manager)
        ScoutConfig.reset_all()


def is_running(core_agent_manager):
    if core_agent_manager.core_agent_bin_path is None:
        return False
    agent_binary = [core_agent_manager.core_agent_bin_path, "probe"]
    socket_path = core_agent_manager.socket_path()
    probe = subprocess.check_output(agent_binary + socket_path)
    if b"Agent found" in probe:
        return True
    if b"Agent Not Running" in probe:
        return False
    raise AssertionError("cannot tell if the core agent is running")


def shutdown(core_agent_manager):
    agent_binary = [core_agent_manager.core_agent_bin_path, "shutdown"]
    socket_path = core_agent_manager.socket_path()
    subprocess.check_call(agent_binary + socket_path)


# Tests must execute in the order in which they are defined.


def test_no_launch(caplog, core_agent_manager):
    ScoutConfig.set(core_agent_launch=False)

    try:
        result = core_agent_manager.launch()
    finally:
        ScoutConfig.set(core_agent_launch=True)

    assert not result
    assert not is_running(core_agent_manager)
    assert caplog.record_tuples == [
        (
            "scout_apm.core.core_agent_manager",
            logging.DEBUG,
            (
                "Not attempting to launch Core Agent due to 'core_agent_launch' "
                + "setting."
            ),
        )
    ]


def test_no_verify(caplog, core_agent_manager):
    ScoutConfig.set(core_agent_download=False)

    try:
        result = core_agent_manager.launch()
    finally:
        ScoutConfig.set(core_agent_download=True)

    assert not result
    assert not is_running(core_agent_manager)
    assert (
        "scout_apm.core.core_agent_manager",
        logging.DEBUG,
        (
            "Not attempting to download Core Agent due to "
            + "'core_agent_download' setting."
        ),
    ) in caplog.record_tuples


def test_download_and_launch(core_agent_manager):
    assert core_agent_manager.launch()
    time.sleep(0.01)  # wait for agent to start running
    assert is_running(core_agent_manager)
    shutdown(core_agent_manager)


def test_verify_error(caplog, core_agent_manager):
    digest_patcher = mock.patch(
        "scout_apm.core.core_agent_manager.sha256_digest",
        return_value="not the expected digest",
    )
    # Patch out the download() method to avoid downloading again the agent and
    # not make the tests slower than necessary.
    download_patcher = mock.patch(
        "scout_apm.core.core_agent_manager.CoreAgentManager.download"
    )

    with digest_patcher, download_patcher:
        result = core_agent_manager.launch()

    assert not result
    assert not is_running(core_agent_manager)
    assert (
        "scout_apm.core.core_agent_manager",
        logging.DEBUG,
        "Failed to verify Core Agent. Not launching Core Agent.",
    ) in caplog.record_tuples


def test_launch_error(caplog, core_agent_manager):
    caplog.set_level(logging.ERROR)
    exception = ValueError("Hello Fail")
    with mock.patch(
        "scout_apm.core.core_agent_manager.CoreAgentManager.agent_binary",
        side_effect=exception,
    ):
        result = core_agent_manager.launch()

    assert not result
    assert not is_running(core_agent_manager)
    assert caplog.record_tuples == [
        ("scout_apm.core.core_agent_manager", logging.ERROR, "Error running Core Agent")
    ]
    assert caplog.records[0].exc_info[1] is exception


def test_log_level(caplog, core_agent_manager):
    ScoutConfig.set(core_agent_log_level="foo")

    result = core_agent_manager.log_level()

    assert result == ["--log-level", "foo"]
    assert caplog.record_tuples == []


def test_log_level_deprecated(caplog, core_agent_manager):
    ScoutConfig.set(log_level="foo", core_agent_log_level="bar")

    result = core_agent_manager.log_level()

    assert result == ["--log-level", "foo"]
    assert caplog.record_tuples == [
        (
            "scout_apm.core.core_agent_manager",
            logging.WARNING,
            (
                "The config name 'log_level' is deprecated - please use the new name "
                + "'core_agent_log_level' instead. This might be configured in your "
                + "environment variables or framework settings as SCOUT_LOG_LEVEL."
            ),
        )
    ]
