from __future__ import absolute_import, division, print_function, unicode_literals

import datetime

import pytest

from scout_apm.core import commands
from scout_apm.core.tracked_request import TrackedRequest

REQUEST_ID = "req-97c1d72c-5519-4665-85d3-1ac21af39b63"
SPAN_ID = "span-7dbb0712-e3c5-4b73-b317-f8d2114c5993"
PARENT_ID = "span-d10de59e-1e9f-46e9-9d5e-81b5bfc091ec"

TIMESTAMP = datetime.datetime(2018, 12, 1, 17, 4, 34, 386568)
TIMESTAMP_STR = "2018-12-01T17:04:34.386568Z"
INVALID_TIMESTAMP_STR = "2000-01-01T00:00:00Z"

START_TIME = datetime.datetime(2018, 12, 1, 17, 4, 34, 78797)
START_TIME_STR = "2018-12-01T17:04:34.078797Z"

END_TIME = datetime.datetime(2018, 12, 1, 17, 4, 34, 641403)
END_TIME_STR = "2018-12-01T17:04:34.641403Z"


@pytest.mark.parametrize(
    "command, message",
    [
        (
            commands.Register(app="test_app", key="test_key"),
            {
                "Register": {
                    "app": "test_app",
                    "key": "test_key",
                    "language": "python",
                    "api_version": "1.0",
                }
            },
        ),
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
            commands.StartSpan(),
            {
                "StartSpan": {
                    "timestamp": INVALID_TIMESTAMP_STR,
                    "request_id": None,
                    "span_id": None,
                    "parent_id": None,
                    "operation": None,
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
            commands.StopSpan(),
            {
                "StopSpan": {
                    "timestamp": INVALID_TIMESTAMP_STR,
                    "request_id": None,
                    "span_id": None,
                }
            },
        ),
        (
            commands.StartRequest(timestamp=TIMESTAMP, request_id=REQUEST_ID),
            {"StartRequest": {"timestamp": TIMESTAMP_STR, "request_id": REQUEST_ID}},
        ),
        (
            commands.StartRequest(),
            {"StartRequest": {"timestamp": INVALID_TIMESTAMP_STR, "request_id": None}},
        ),
        (
            commands.FinishRequest(timestamp=TIMESTAMP, request_id=REQUEST_ID),
            {"FinishRequest": {"timestamp": TIMESTAMP_STR, "request_id": REQUEST_ID}},
        ),
        (
            commands.FinishRequest(),
            {"FinishRequest": {"timestamp": INVALID_TIMESTAMP_STR, "request_id": None}},
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
            commands.TagSpan(),
            {
                "TagSpan": {
                    "timestamp": INVALID_TIMESTAMP_STR,
                    "request_id": None,
                    "span_id": None,
                    "tag": None,
                    "value": None,
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
            commands.TagRequest(),
            {
                "TagRequest": {
                    "timestamp": INVALID_TIMESTAMP_STR,
                    "request_id": None,
                    "tag": None,
                    "value": None,
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
            commands.ApplicationEvent(),
            {
                "ApplicationEvent": {
                    "timestamp": INVALID_TIMESTAMP_STR,
                    "event_type": "",
                    "event_value": "",
                    "source": "",
                }
            },
        ),
        (commands.CoreAgentVersion(), {"CoreAgentVersion": {}}),
        (
            commands.BatchCommand(
                [
                    commands.CoreAgentVersion(),
                    commands.StartRequest(timestamp=TIMESTAMP, request_id=REQUEST_ID),
                    commands.FinishRequest(timestamp=TIMESTAMP, request_id=REQUEST_ID),
                ]
            ),
            {
                "BatchCommand": {
                    "commands": [
                        {"CoreAgentVersion": {}},
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


def test_core_agent_version_response():
    command = commands.CoreAgentVersionResponse(
        '{"CoreAgentVersion": {"version": "x.y"}}'
    )
    assert command.version == "x.y"


def make_tracked_request_instance_deterministic(tr):
    """
    Override values in a TrackedRequest instance to make tests determistic.

    """
    assert type(tr.req_id) == type(REQUEST_ID)
    tr.req_id = REQUEST_ID

    assert type(tr.start_time) == type(START_TIME)
    tr.start_time = START_TIME

    if tr.end_time is not None:
        assert type(tr.end_time) == type(END_TIME)
        tr.end_time = END_TIME

    for span in tr.active_spans + tr.complete_spans:
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


def test_batch_command_from_tracked_request():
    tr = TrackedRequest()
    tr.finish()
    make_tracked_request_instance_deterministic(tr)
    command = commands.BatchCommand.from_tracked_request(tr)
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
    tr = TrackedRequest()
    tr.tag("test_key", "test_value")
    tr.finish()
    make_tracked_request_instance_deterministic(tr)
    command = commands.BatchCommand.from_tracked_request(tr)
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


def test_batch_command_from_tracked_request_with_unfinished_request():
    tr = TrackedRequest()
    make_tracked_request_instance_deterministic(tr)
    command = commands.BatchCommand.from_tracked_request(tr)
    assert command is None


def test_batch_command_from_tracked_request_with_span():
    tr = TrackedRequest()
    tr.start_span()
    tr.stop_span()
    make_tracked_request_instance_deterministic(tr)
    command = commands.BatchCommand.from_tracked_request(tr)
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
                    "StartSpan": {
                        "operation": None,
                        "parent_id": None,
                        "request_id": REQUEST_ID,
                        "span_id": SPAN_ID,
                        "timestamp": START_TIME_STR,
                    }
                },
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
                    "StopSpan": {
                        "request_id": REQUEST_ID,
                        "span_id": SPAN_ID,
                        "timestamp": END_TIME_STR,
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


def test_batch_command_from_tracked_request_with_unfinished_span():
    tr = TrackedRequest()
    tr.start_span()
    make_tracked_request_instance_deterministic(tr)
    command = commands.BatchCommand.from_tracked_request(tr)
    assert command is None


def test_batch_command_from_tracked_request_with_finished_span_but_no_end_time():
    tr = TrackedRequest()
    tr.start_span()
    tr.stop_span()
    # Not sure how this can happen, but the code currently handles this case.
    tr.complete_spans[0].end_time = None
    make_tracked_request_instance_deterministic(tr)
    command = commands.BatchCommand.from_tracked_request(tr)
    assert command is None
