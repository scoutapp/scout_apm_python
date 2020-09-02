# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import time

from scout_apm.core.config import scout_config
from scout_apm.core.core_agent_manager import CoreAgentManager
from tests.compat import mock
from tests.conftest import is_running, shutdown

# Tests must execute in the order in which they are defined.


def test_no_launch(caplog, core_agent_manager):
    scout_config.set(core_agent_launch=False)

    try:
        result = core_agent_manager.launch()
    finally:
        scout_config.set(core_agent_launch=True)

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
    scout_config.set(core_agent_download=False)

    try:
        result = core_agent_manager.launch()
    finally:
        scout_config.set(core_agent_download=True)

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
    time.sleep(0.10)  # wait for agent to start running
    for _ in range(10):
        if is_running(core_agent_manager):
            break
        time.sleep(0.1)
    else:
        raise AssertionError("Could not find core agent running")
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
    with mock.patch.object(
        CoreAgentManager,
        "agent_binary",
        side_effect=exception,
    ):
        result = core_agent_manager.launch()

    assert not result
    assert not is_running(core_agent_manager)
    assert caplog.record_tuples == [
        ("scout_apm.core.core_agent_manager", logging.ERROR, "Error running Core Agent")
    ]
    assert caplog.records[0].exc_info[1] is exception
