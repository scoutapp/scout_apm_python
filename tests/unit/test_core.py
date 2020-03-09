# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import os

from scout_apm.api import Config
from scout_apm.core import install, shutdown
from scout_apm.core.config import scout_config
from scout_apm.core.core_agent_manager import CoreAgentManager
from scout_apm.core.metadata import report_app_metadata
from tests.compat import mock


def test_install_fail_windows(caplog):
    with mock.patch.object(os, "name", new="nt"):
        installed = install()

    assert installed is False
    assert (
        "scout_apm.core",
        logging.INFO,
        "APM Not Launching on PID: %s - Windows is not supported" % os.getpid(),
    ) in caplog.record_tuples


def test_install_fail_monitor_false(caplog):
    try:
        installed = install(config={"monitor": False})
    finally:
        Config.reset_all()

    assert installed is False
    assert (
        "scout_apm.core",
        logging.INFO,
        (
            "APM Not Launching on PID: %s - Configuration 'monitor' is not true"
            % os.getpid()
        ),
    ) in caplog.record_tuples


def test_install_success(caplog):
    with mock.patch.object(CoreAgentManager, "launch"):
        try:
            installed = install(config={"monitor": True})
        finally:
            Config.reset_all()

    assert installed is True
    assert (
        "scout_apm.core",
        logging.DEBUG,
        "APM Launching on PID: %s" % os.getpid(),
    ) in caplog.record_tuples


def test_shutdown(capsys):
    scout_config
    report_app_metadata()  # queued but thread not running
    try:
        scout_config.set(shutdown_timeout_seconds=0.1)

        shutdown()
    finally:
        Config.reset_all()

    captured = capsys.readouterr()
    assert "Scout draining" in captured.err


def test_shutdown_message_disabled(capsys):
    report_app_metadata()  # queued but thread not running
    try:
        scout_config.set(shutdown_timeout_seconds=0.1, shutdown_message_enabled=False)

        shutdown()
    finally:
        Config.reset_all()

    captured = capsys.readouterr()
    assert not captured.err
