# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import time

import pytest

from scout_apm.core.socket import CoreAgentSocketThread
from tests.compat import mock
from tests.conftest import core_agent_is_running, terminate_core_agent_processes


@pytest.fixture
def running_agent(core_agent_manager):
    assert not core_agent_is_running()
    assert core_agent_manager.launch()

    # Wait for agent to start running
    for _ in range(400):
        if core_agent_is_running():
            break
        time.sleep(0.01)
    else:
        raise AssertionError("Core agent did not start in 4 second")

    try:
        yield
    finally:
        terminate_core_agent_processes()
        assert not core_agent_is_running()


@pytest.fixture
def socket(running_agent):
    socket = CoreAgentSocketThread.ensure_started()
    # Wait for socket to connect and register:
    time.sleep(0.01)

    yield socket
    # ensure_stopped() already called by global auto_stop_core_agent_socket


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


def test_wait_until_drained_empty(socket):
    empty = CoreAgentSocketThread.wait_until_drained()
    assert empty


def test_wait_until_drained_one_item(socket):
    CoreAgentSocketThread._command_queue.put(Command(), False)

    empty = CoreAgentSocketThread.wait_until_drained()
    assert empty


def test_wait_until_drained_one_slow(socket):
    class SlowCommand(object):
        def message(self):
            time.sleep(0.05)
            return {}

    for _ in range(10):
        CoreAgentSocketThread.send(SlowCommand())

    empty = CoreAgentSocketThread.wait_until_drained(timeout_seconds=0.05)
    assert not empty
