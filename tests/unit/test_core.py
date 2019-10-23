# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import os
import sys

from scout_apm.api import Config
from scout_apm.core import install
from scout_apm.core.core_agent_manager import CoreAgentManager
from tests.compat import mock


def test_install_fail_windows(caplog):
    with mock.patch.object(sys, "platform", new="win32"):
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
