# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import time

import pytest

from scout_apm.core.socket import CoreAgentSocketThread
from tests.compat import mock
from tests.conftest import is_running, shutdown


@pytest.fixture
def running_agent(core_agent_manager):
    assert not is_running(core_agent_manager)
    assert core_agent_manager.launch()
    time.sleep(0.01)  # wait for agent to start running
    assert is_running(core_agent_manager)
    try:
        yield
    finally:
        shutdown(core_agent_manager)
        assert not is_running(core_agent_manager)


@pytest.fixture
def socket(running_agent):
    socket = CoreAgentSocketThread.ensure_started()
    try:
        # Wait for socket to connect and register:
        time.sleep(0.01)

        yield socket
    finally:
        CoreAgentSocketThread.ensure_stopped()


class Command(object):
    def message(self):
        return {}


def test_send(socket):
    CoreAgentSocketThread.send(Command())


class NonSerializableCommand(object):
    def message(self):
        return object()


def test_send_serialization_error(socket):
    CoreAgentSocketThread.send(NonSerializableCommand())


@mock.patch("socket.socket.sendall")
def test_send_network_error(sendall, socket):
    sendall.side_effect = OSError
    CoreAgentSocketThread.send(Command())
