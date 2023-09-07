# coding=utf-8

import logging
import signal
import subprocess
import time

import pytest

from scout_apm.core.agent import manager
from scout_apm.core.config import scout_config
from tests.compat import mock
from tests.conftest import core_agent_is_running, terminate_core_agent_processes

# Tests must execute in the order in which they are defined.


def test_no_launch(caplog, core_agent_manager):
    scout_config.set(core_agent_launch=False)

    try:
        result = core_agent_manager.launch()
    finally:
        scout_config.set(core_agent_launch=True)

    assert not result
    assert not core_agent_is_running()
    assert caplog.record_tuples == [
        (
            "scout_apm.core.agent.manager",
            logging.DEBUG,
            (
                "Not attempting to launch Core Agent due to 'core_agent_launch' "
                + "setting."
            ),
        )
    ]


def test_no_verify(caplog, core_agent_manager):
    scout_config.set(core_agent_download=False)

    try:
        result = core_agent_manager.launch()
    finally:
        scout_config.set(core_agent_download=True)

    assert not result
    assert not core_agent_is_running()
    assert (
        "scout_apm.core.agent.manager",
        logging.DEBUG,
        (
            "Not attempting to download Core Agent due to "
            + "'core_agent_download' setting."
        ),
    ) in caplog.record_tuples


@pytest.mark.parametrize(
    "path",
    [
        None,
        "tcp://127.0.0.1:5678",
        "/tmp/scout-tests.sock",
    ],
)
def test_download_and_launch(path, core_agent_manager):
    if path is not None:
        scout_config.set(core_agent_socket_path=path)

    try:
        result = core_agent_manager.launch()

        assert result is True

        time.sleep(0.10)  # wait for agent to start running
        for _ in range(10):
            if core_agent_is_running():
                break
            time.sleep(0.1)
        else:
            raise AssertionError("Could not find core agent running")

        terminate_core_agent_processes()
    finally:
        scout_config.reset_all()


def test_verify_error(caplog, core_agent_manager):
    digest_patcher = mock.patch.object(
        manager,
        "sha256_digest",
        return_value="not the expected digest",
    )
    # Patch out the download() method to avoid downloading again the agent and
    # not make the tests slower than necessary.
    download_patcher = mock.patch.object(manager.CoreAgentManager, "download")

    with digest_patcher, download_patcher:
        result = core_agent_manager.launch()

    assert not result
    assert not core_agent_is_running()
    assert (
        "scout_apm.core.agent.manager",
        logging.DEBUG,
        "Failed to verify Core Agent. Not launching Core Agent.",
    ) in caplog.record_tuples


def test_launch_error(caplog, core_agent_manager):
    caplog.set_level(logging.ERROR)
    exception = ValueError("Hello Fail")
    with mock.patch.object(
        manager.CoreAgentManager,
        "agent_binary",
        side_effect=exception,
    ):
        result = core_agent_manager.launch()

    assert not result
    assert not core_agent_is_running()
    assert caplog.record_tuples == [
        ("scout_apm.core.agent.manager", logging.ERROR, "Error running Core Agent")
    ]
    assert caplog.records[0].exc_info[1] is exception


@pytest.mark.parametrize(["signal_code"], [[signal.SIGQUIT], [signal.SIGTERM]])
def test_launch_expected_signal_error(signal_code, caplog, core_agent_manager):
    caplog.set_level(logging.ERROR)
    exception = subprocess.CalledProcessError(signal_code, "err")
    with mock.patch.object(
        manager.CoreAgentManager,
        "agent_binary",
        side_effect=exception,
    ):
        result = core_agent_manager.launch()

    assert not result
    assert not core_agent_is_running()
    # Caplog doesn't contain debug messages
    assert caplog.record_tuples == []


def test_launch_unexpected_signal_error(caplog, core_agent_manager):
    caplog.set_level(logging.ERROR)
    exception = subprocess.CalledProcessError(signal.SIGINT, "err")
    with mock.patch.object(
        manager.CoreAgentManager,
        "agent_binary",
        side_effect=exception,
    ):
        result = core_agent_manager.launch()

    assert not result
    assert not core_agent_is_running()
    assert caplog.record_tuples == [
        (
            "scout_apm.core.agent.manager",
            logging.ERROR,
            "CalledProcessError running Core Agent",
        )
    ]
    assert caplog.records[0].exc_info[1] is exception
