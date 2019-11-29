# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import time

import pytest

from scout_apm.core.socket import CoreAgentSocket
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
    socket = CoreAgentSocket.instance()
    try:
        time.sleep(0.01)  # wait for socket to connect and register
        yield socket
    finally:
        socket.stop()
        socket.join()


def test_socket_instance_is_a_singleton(running_agent):
    socket1 = CoreAgentSocket.instance()
    socket2 = CoreAgentSocket.instance()
    try:
        assert socket2 is socket1
    finally:
        socket1.stop()
        socket1.join()
        socket2.stop()
        socket2.join()


def test_socket_instance_is_recreated_if_not_running(running_agent):
    socket1 = CoreAgentSocket.instance()
    socket1.stop()
    socket1.join()
    socket2 = CoreAgentSocket.instance()
    try:
        assert socket2 is not socket1
    finally:
        socket2.stop()
        socket2.join()


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


@mock.patch("socket.socket.sendall")
def test_send_network_error(sendall, socket):
    sendall.side_effect = OSError
    socket.send(Command())
