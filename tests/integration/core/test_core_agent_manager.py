from __future__ import absolute_import, division, print_function, unicode_literals

import subprocess
import time

import pytest

from scout_apm.core.config import ScoutConfig
from scout_apm.core.context import AgentContext
from scout_apm.core.core_agent_manager import CoreAgentManager

try:
    from unittest.mock import patch
except ImportError:  # Python 2.7
    from mock import patch


@pytest.fixture
def core_agent_manager(core_agent_dir):
    # Shorten path to socket to prevent core-agent from failing with:
    #   Error opening listener on socket: Custom { kind: InvalidInput,
    #   error: StringError("path must be shorter than SUN_LEN") }
    socket_path = "{}/test.sock".format(core_agent_dir)
    ScoutConfig.set(core_agent_dir=core_agent_dir, socket_path=socket_path)
    AgentContext.build()
    try:
        yield CoreAgentManager()
    finally:
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
    assert False, "cannot tell if the core agent is running"


def shutdown(core_agent_manager):
    agent_binary = [core_agent_manager.core_agent_bin_path, "shutdown"]
    socket_path = core_agent_manager.socket_path()
    subprocess.check_call(agent_binary + socket_path)


# Tests must execute in the order in which they are defined.


@patch("scout_apm.core.core_agent_manager.logger")
def test_no_launch(logger, core_agent_manager):
    ScoutConfig.set(core_agent_launch=False)
    try:
        assert not core_agent_manager.launch()
        assert not is_running(core_agent_manager)
        logger.debug.assert_called_with(
            "Not attempting to launch Core Agent due to 'core_agent_launch' setting."
        )
    finally:
        ScoutConfig.set(core_agent_launch=True)


@patch("scout_apm.core.core_agent_manager.logger")
def test_no_verify(logger, core_agent_manager):
    ScoutConfig.set(core_agent_download=False)
    try:
        assert not core_agent_manager.launch()
        assert not is_running(core_agent_manager)
        logger.debug.assert_called_with(
            "Not attempting to download Core Agent "
            "due to 'core_agent_download' setting."
        )
    finally:
        ScoutConfig.set(core_agent_download=True)


def test_download_and_launch(core_agent_manager):
    assert core_agent_manager.launch()
    time.sleep(0.01)  # wait for agent to start running
    assert is_running(core_agent_manager)
    shutdown(core_agent_manager)


@patch("scout_apm.core.core_agent_manager.logger")
def test_verify_error(logger, core_agent_manager):
    with patch(
        "scout_apm.core.core_agent_manager.SHA256.digest",
        return_value="not the expected digest",
    ):
        # Patch out the download() method to avoid downloading again
        # the agent and not make the tests slower than necessary.
        with patch("scout_apm.core.core_agent_manager.CoreAgentManager.download"):
            assert not core_agent_manager.launch()
            assert not is_running(core_agent_manager)
            logger.debug.assert_called_with(
                "Failed to verify Core Agent. Not launching Core Agent."
            )


@patch("scout_apm.core.core_agent_manager.logger")
def test_launch_error(logger, core_agent_manager):
    with patch(
        "scout_apm.core.core_agent_manager.CoreAgentManager.agent_binary",
        return_value=[core_agent_manager.core_agent_bin_path, "fail"],
    ):
        assert not core_agent_manager.launch()
        assert not is_running(core_agent_manager)
        assert logger.error.call_count >= 1
