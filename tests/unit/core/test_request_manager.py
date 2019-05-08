# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import pytest

from scout_apm.core.context import AgentContext
from scout_apm.core.request_manager import RequestManager
from scout_apm.core.tracked_request import TrackedRequest

from .test_commands import (
    END_TIME,
    END_TIME_STR,
    REQUEST_ID,
    START_TIME,
    START_TIME_STR,
)

try:
    from unittest.mock import patch
except ImportError:  # Python 2.7
    from mock import patch


@pytest.fixture
def tracked_request():
    # Create a complete tracked request without calling its finalize() method
    # because it calls RequestManager.add_request(). This is too much coupling
    # for testing RequestManager in isolation.
    request = TrackedRequest()
    request.req_id = REQUEST_ID
    request.start_time = START_TIME
    request.end_time = END_TIME
    request.real_request = True
    return request


# Flushing at every request seems to defeat the point of buffering.
# However this is the current behavior, so let's test it.
@patch("scout_apm.core.socket.CoreAgentSocket.send")
def test_add_request_flushes_every_request(send, tracked_request):
    AgentContext.build()

    manager = RequestManager()
    manager.add_request(tracked_request)

    assert send.call_count == 1
    (command,), kwargs = send.call_args
    assert kwargs == {}

    message = command.message()
    assert message == {
        "BatchCommand": {
            "commands": [
                {
                    "StartRequest": {
                        "request_id": REQUEST_ID,
                        "timestamp": START_TIME_STR,
                    }
                },
                {
                    "FinishRequest": {
                        "request_id": REQUEST_ID,
                        "timestamp": END_TIME_STR,
                    }
                },
            ]
        }
    }

    assert not manager.request_buffer._requests  # buffer is empty


@patch("scout_apm.core.socket.CoreAgentSocket.send")
def test_add_request_handles_only_finished_requests(send, tracked_request):
    AgentContext.build()

    tracked_request.end_time = None

    manager = RequestManager()
    manager.add_request(tracked_request)

    send.assert_not_called()

    assert not manager.request_buffer._requests  # buffer is empty


@patch("scout_apm.core.socket.CoreAgentSocket.send")
def test_add_request_handles_only_real_requests(send, tracked_request):
    AgentContext.build()

    tracked_request.real_request = False

    manager = RequestManager()
    manager.add_request(tracked_request)

    send.assert_not_called()

    assert not manager.request_buffer._requests  # buffer is empty
