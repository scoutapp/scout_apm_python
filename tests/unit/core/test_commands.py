# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime as dt
import logging

import pytest

from scout_apm.core import commands
from scout_apm.core.tracked_request import TrackedRequest
from tests.tools import skip_if_objtrace_not_extension

REQUEST_ID = "req-97c1d72c-5519-4665-85d3-1ac21af39b63"
SPAN_ID = "span-7dbb0712-e3c5-4b73-b317-f8d2114c5993"
PARENT_ID = "span-d10de59e-1e9f-46e9-9d5e-81b5bfc091ec"

TIMESTAMP = dt.datetime(2018, 12, 1, 17, 4, 34, 386568)
TIMESTAMP_STR = "2018-12-01T17:04:34.386568Z"

START_TIME = dt.datetime(2018, 12, 1, 17, 4, 34, 78797)
START_TIME_STR = "2018-12-01T17:04:34.078797Z"

END_TIME = dt.datetime(2018, 12, 1, 17, 4, 34, 641403)
END_TIME_STR = "2018-12-01T17:04:34.641403Z"


def test_register_message_good_key(caplog):
    command = commands.Register(
        app="test_app", key="abcdefghijabcdef", hostname="test_host"
    )

    assert command.message() == {
        "Register": {
            "app": "test_app",
            "key": "abcdefghijabcdef",
            "host": "test_host",
            "language": "python",
            "api_version": "1.0",
        }
    }
    assert caplog.record_tuples == [
        (
            "scout_apm.core.commands",
            logging.INFO,
            (
                "Registering with app=test_app key_prefix=abc"
                + " key_format_validated=True host=test_host"
            ),
        )
    ]


def test_register_message_bad_key(caplog):
    command = commands.Register(
        app="test_app", key="whoops-pasted-it-in-wrong", hostname="test_host"
    )

    assert command.message() == {
        "Register": {
            "app": "test_app",
            "key": "whoops-pasted-it-in-wrong",
            "host": "test_host",
            "language": "python",
            "api_version": "1.0",
        }
    }
    assert caplog.record_tuples == [
        (
            "scout_apm.core.commands",
            logging.INFO,
            (
                "Registering with app=test_app key_prefix=who"
                + " key_format_validated=False host=test_host"
            ),
        )
    ]


@pytest.mark.parametrize(
    "command, message",
    [
        (
            commands.StartSpan(
                timestamp=TIMESTAMP,
                request_id=REQUEST_ID,
                span_id=SPAN_ID,
                parent=PARENT_ID,
                operation="Test/Run",
            ),
            {
                "StartSpan": {
                    "timestamp": TIMESTAMP_STR,
                    "request_id": REQUEST_ID,
                    "span_id": SPAN_ID,
                    "parent_id": PARENT_ID,
                    "operation": "Test/Run",
                }
            },
        ),
        (
            commands.StopSpan(
                timestamp=TIMESTAMP, request_id=REQUEST_ID, span_id=SPAN_ID
            ),
            {
                "StopSpan": {
                    "timestamp": TIMESTAMP_STR,
                    "request_id": REQUEST_ID,
                    "span_id": SPAN_ID,
                }
            },
        ),
        (
            commands.StartRequest(timestamp=TIMESTAMP, request_id=REQUEST_ID),
            {"StartRequest": {"timestamp": TIMESTAMP_STR, "request_id": REQUEST_ID}},
        ),
        (
            commands.FinishRequest(timestamp=TIMESTAMP, request_id=REQUEST_ID),
            {"FinishRequest": {"timestamp": TIMESTAMP_STR, "request_id": REQUEST_ID}},
        ),
        (
            commands.TagSpan(
                timestamp=TIMESTAMP,
                request_id=REQUEST_ID,
                span_id=SPAN_ID,
                tag="test_tag",
                value="test_value",
            ),
            {
                "TagSpan": {
                    "timestamp": TIMESTAMP_STR,
                    "request_id": REQUEST_ID,
                    "span_id": SPAN_ID,
                    "tag": "test_tag",
                    "value": "test_value",
                }
            },
        ),
        (
            commands.TagRequest(
                timestamp=TIMESTAMP,
                request_id=REQUEST_ID,
                tag="test_tag",
                value="test_value",
            ),
            {
                "TagRequest": {
                    "timestamp": TIMESTAMP_STR,
                    "request_id": REQUEST_ID,
                    "tag": "test_tag",
                    "value": "test_value",
                }
            },
        ),
        (
            commands.ApplicationEvent(
                timestamp=TIMESTAMP,
                event_type="test_event",
                event_value="test_value",
                source="test_source",
            ),
            {
                "ApplicationEvent": {
                    "timestamp": TIMESTAMP_STR,
                    "event_type": "test_event",
                    "event_value": "test_value",
                    "source": "test_source",
                }
            },
        ),
        (
            commands.BatchCommand(
                [
                    commands.StartRequest(timestamp=TIMESTAMP, request_id=REQUEST_ID),
                    commands.FinishRequest(timestamp=TIMESTAMP, request_id=REQUEST_ID),
                ]
            ),
            {
                "BatchCommand": {
                    "commands": [
                        {
                            "StartRequest": {
                                "timestamp": TIMESTAMP_STR,
                                "request_id": REQUEST_ID,
                            }
                        },
                        {
                            "FinishRequest": {
                                "timestamp": TIMESTAMP_STR,
                                "request_id": REQUEST_ID,
                            }
                        },
                    ]
                }
            },
        ),
    ],
)
def test_command_message(command, message):
    assert command.message() == message


def make_tracked_request_instance_deterministic(tracked_request):
    """
    Override values in a TrackedRequest instance to make tests determistic.

    """
    assert type(tracked_request.request_id) == type(REQUEST_ID)
    tracked_request.request_id = REQUEST_ID

    assert type(tracked_request.start_time) == type(START_TIME)
    tracked_request.start_time = START_TIME

    if tracked_request.end_time is not None:
        assert type(tracked_request.end_time) == type(END_TIME)
        tracked_request.end_time = END_TIME

    for span in tracked_request.active_spans + tracked_request.complete_spans:
        assert type(span.request_id) == type(REQUEST_ID)
        span.request_id = REQUEST_ID

        assert type(span.span_id) == type(SPAN_ID)
        span.span_id = SPAN_ID

        assert type(span.start_time) == type(START_TIME)
        span.start_time = START_TIME

        if span.end_time is not None:
            assert type(span.end_time) == type(END_TIME)
            span.end_time = END_TIME

        if "allocations" in span.tags:
            span.tags["allocations"] = 0
        if "start_allocations" in span.tags:
            span.tags["start_allocations"] = 0
        if "stop_allocations" in span.tags:
            span.tags["stop_allocations"] = 0


def test_batch_command_from_tracked_request():
    tracked_request = TrackedRequest()
    tracked_request.finish()
    make_tracked_request_instance_deterministic(tracked_request)
    command = commands.BatchCommand.from_tracked_request(tracked_request)
    assert command.message() == {
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


def test_batch_command_from_tracked_request_with_tag():
    tracked_request = TrackedRequest()
    tracked_request.tag("test_key", "test_value")
    tracked_request.finish()
    make_tracked_request_instance_deterministic(tracked_request)
    command = commands.BatchCommand.from_tracked_request(tracked_request)
    assert command.message() == {
        "BatchCommand": {
            "commands": [
                {
                    "StartRequest": {
                        "request_id": REQUEST_ID,
                        "timestamp": START_TIME_STR,
                    }
                },
                {
                    "TagRequest": {
                        "request_id": REQUEST_ID,
                        "timestamp": START_TIME_STR,
                        "tag": "test_key",
                        "value": "test_value",
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


@skip_if_objtrace_not_extension
def test_batch_command_from_tracked_request_with_span():
    tracked_request = TrackedRequest()
    tracked_request.start_span("myoperation")
    tracked_request.stop_span()
    make_tracked_request_instance_deterministic(tracked_request)

    command = commands.BatchCommand.from_tracked_request(tracked_request)

    message_commands = command.message()["BatchCommand"]["commands"]
    assert len(message_commands) == 7
    assert message_commands[0] == {
        "StartRequest": {"request_id": REQUEST_ID, "timestamp": START_TIME_STR}
    }
    assert message_commands[1] == {
        "StartSpan": {
            "operation": "myoperation",
            "parent_id": None,
            "request_id": REQUEST_ID,
            "span_id": SPAN_ID,
            "timestamp": START_TIME_STR,
        }
    }
    assert sorted(message_commands[2:5], key=lambda c: c["TagSpan"]["tag"]) == [
        {
            "TagSpan": {
                "request_id": REQUEST_ID,
                "span_id": SPAN_ID,
                "tag": "allocations",
                "timestamp": START_TIME_STR,
                "value": 0,
            }
        },
        {
            "TagSpan": {
                "request_id": REQUEST_ID,
                "span_id": SPAN_ID,
                "tag": "start_allocations",
                "timestamp": START_TIME_STR,
                "value": 0,
            }
        },
        {
            "TagSpan": {
                "request_id": REQUEST_ID,
                "span_id": SPAN_ID,
                "tag": "stop_allocations",
                "timestamp": START_TIME_STR,
                "value": 0,
            }
        },
    ]
    assert message_commands[5] == {
        "StopSpan": {
            "request_id": REQUEST_ID,
            "span_id": SPAN_ID,
            "timestamp": END_TIME_STR,
        }
    }
    assert message_commands[6] == {
        "FinishRequest": {"request_id": REQUEST_ID, "timestamp": END_TIME_STR}
    }


@skip_if_objtrace_not_extension
def test_batch_command_from_tracked_request_with_span_no_objtrace():
    tracked_request = TrackedRequest()
    tracked_request.start_span(operation="myoperation")
    tracked_request.stop_span()
    make_tracked_request_instance_deterministic(tracked_request)

    command = commands.BatchCommand.from_tracked_request(tracked_request)

    message_commands = command.message()["BatchCommand"]["commands"]
    assert len(message_commands) == 7
    assert message_commands[0] == {
        "StartRequest": {"request_id": REQUEST_ID, "timestamp": START_TIME_STR}
    }
    assert message_commands[1] == {
        "StartSpan": {
            "operation": "myoperation",
            "parent_id": None,
            "request_id": REQUEST_ID,
            "span_id": SPAN_ID,
            "timestamp": START_TIME_STR,
        }
    }
    assert sorted(message_commands[2:5], key=lambda c: c["TagSpan"]["tag"]) == [
        {
            "TagSpan": {
                "timestamp": START_TIME_STR,
                "request_id": REQUEST_ID,
                "span_id": SPAN_ID,
                "tag": "allocations",
                "value": 0,
            }
        },
        {
            "TagSpan": {
                "timestamp": START_TIME_STR,
                "request_id": REQUEST_ID,
                "span_id": SPAN_ID,
                "tag": "start_allocations",
                "value": 0,
            }
        },
        {
            "TagSpan": {
                "timestamp": START_TIME_STR,
                "request_id": REQUEST_ID,
                "span_id": SPAN_ID,
                "tag": "stop_allocations",
                "value": 0,
            }
        },
    ]
    assert message_commands[5] == {
        "StopSpan": {
            "request_id": REQUEST_ID,
            "span_id": SPAN_ID,
            "timestamp": END_TIME_STR,
        }
    }
    assert message_commands[6] == {
        "FinishRequest": {"request_id": REQUEST_ID, "timestamp": END_TIME_STR}
    }
