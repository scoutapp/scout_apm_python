from __future__ import absolute_import, division, print_function, unicode_literals

import time

import pytest

from scout_apm.core import socket as scout_apm_core_socket
from scout_apm.core.socket import CoreAgentSocket

from .test_core_agent_manager import (  # noqa: F401
    core_agent_manager,
    is_running,
    shutdown,
)

try:
    from unittest.mock import patch
except ImportError:  # Python 2.7
    from mock import patch


@pytest.fixture  # noqa: F811
def running_agent(core_agent_manager):
    assert not is_running(core_agent_manager)
    assert core_agent_manager.launch()
    time.sleep(0.01)  # wait for agent to start running
    assert is_running(core_agent_manager)
    try:
        yield
    finally:
        shutdown(core_agent_manager)


@pytest.fixture
def socket(running_agent):
    socket = CoreAgentSocket.instance()
    # Make all timeouts shorter so tests that exercise them run faster
    scout_apm_core_socket.SECOND = 0.01
    try:
        time.sleep(0.01)  # wait for socket to connect and register
        yield socket
    finally:
        scout_apm_core_socket.SECOND = 1
        socket.stop()


def test_socket_instance_is_a_singleton(running_agent):
    socket1 = CoreAgentSocket.instance()
    socket2 = CoreAgentSocket.instance()
    try:
        assert socket2 is socket1
    finally:
        socket1.stop()
        socket2.stop()


def test_socket_instance_is_recreated_if_not_running(running_agent):
    socket1 = CoreAgentSocket.instance()
    socket1.stop()
    socket2 = CoreAgentSocket.instance()
    try:
        assert socket2 is not socket1
    finally:
        socket2.stop()


class Command(object):
    def message(self):
        return {}


def test_send(socket):
    socket.send(Command())


class NonSerializableCommand(object):
    def message(self):
        return object()


def test_send_serialization_error(socket):
    socket.send(NonSerializableCommand())


@patch("socket.socket.sendall")
def test_send_network_error(sendall, socket):
    sendall.side_effect = OSError
    socket.send(Command())
