# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime as dt
import logging

import pytest

from scout_apm.core import objtrace
from scout_apm.core.config import scout_config
from scout_apm.core.tracked_request import TrackedRequest
from tests.compat import copy_context, mock
from tests.tools import (
    skip_if_missing_context_vars,
    skip_if_objtrace_is_extension,
    skip_if_objtrace_not_extension,
)


@pytest.fixture
def reset_config():
    """
    Reset scout configuration after a test
    """
    try:
        yield
    finally:
        # Reset Scout configuration.
        scout_config.reset_all()


def test_tracked_request_repr(tracked_request):
    assert repr(tracked_request).startswith("<TrackedRequest(")


def test_tracked_request_instance_is_a_singleton():
    tracked_request_1 = TrackedRequest.instance()
    tracked_request_2 = TrackedRequest.instance()
    try:
        assert tracked_request_2 is tracked_request_1
    finally:
        tracked_request_1.finish()
        tracked_request_2.finish()


@skip_if_missing_context_vars
def test_tracked_request_copied_into_new_context(tracked_request):
    ctx = copy_context()

    def generate_new_tracked_request(existing_tracked_request):
        new_tracked_request = TrackedRequest.instance()
        assert existing_tracked_request is new_tracked_request

    ctx.run(generate_new_tracked_request, tracked_request)


def test_is_real_request_default_false(tracked_request):
    assert not tracked_request.is_real_request


def test_tag_request(tracked_request):
    tracked_request.tag("foo", "bar")
    assert tracked_request.tags == {"foo": "bar"}


def test_tag_request_overwrite(tracked_request):
    tracked_request.tag("foo", "bar")
    tracked_request.tag("foo", "baz")

    assert tracked_request.tags == {"foo": "baz"}


def test_span_repr(tracked_request):
    span = tracked_request.start_span(operation="myoperation")
    repr_ = repr(span)
    tracked_request.stop_span()

    assert repr_.startswith("<Span(")
    assert "operation='myoperation'" in repr_


def test_tag_span(tracked_request):
    with tracked_request.span(operation="myoperation") as span:
        span.tag("foo", "bar")

    assert tracked_request.complete_spans[0].tags["foo"] == "bar"


def test_tag_span_overwrite(tracked_request):
    span = tracked_request.start_span(operation="myoperation")
    span.tag("foo", "bar")
    span.tag("foo", "baz")
    tracked_request.stop_span()

    assert tracked_request.complete_spans[0].tags["foo"] == "baz"


def test_start_span_wires_parents(tracked_request):
    span1 = tracked_request.start_span(operation="myoperation")
    span2 = tracked_request.start_span(operation="myoperation2")
    assert span1.parent is None
    assert span2.parent == span1.span_id


@skip_if_objtrace_not_extension
def test_tags_allocations_for_spans(tracked_request):
    objtrace.enable()
    span = tracked_request.start_span(operation="myoperation")
    tracked_request.stop_span()
    assert span.tags["allocations"] > 0


@skip_if_objtrace_is_extension
def test_tags_allocations_for_spans_no_objtrace_extension(tracked_request):
    objtrace.enable()
    span = tracked_request.start_span(operation="myoperation")
    tracked_request.stop_span()
    assert "allocations" not in span.tags


def test_start_span_does_not_ignore_children(tracked_request):
    with tracked_request.span(operation="parent"):
        with tracked_request.span(operation="myoperation") as child1:
            with tracked_request.span(operation="myoperation") as child2:
                pass

    assert not child1.ignore
    assert not child1.ignore_children
    assert not child2.ignore
    assert not child2.ignore_children
    assert len(tracked_request.complete_spans) == 3
    assert tracked_request.complete_spans[2].operation == "parent"


def test_start_span_ignores_children(tracked_request):
    tracked_request.start_span(operation="parent", ignore_children=True)
    child1 = tracked_request.start_span(operation="child1")
    assert child1.ignore
    assert child1.ignore_children
    child2 = tracked_request.start_span(operation="child2")
    assert child2.ignore
    assert child2.ignore_children
    tracked_request.stop_span()
    tracked_request.stop_span()
    tracked_request.stop_span()
    assert 1 == len(tracked_request.complete_spans)
    assert "parent" == tracked_request.complete_spans[0].operation


@mock.patch("scout_apm.core.tracked_request.TrackedRequest.MAX_COMPLETE_SPANS", new=1)
def test_start_span_at_max_ignores_span(caplog, tracked_request):
    tracked_request.start_span(operation="parent")
    tracked_request.start_span(operation="child1")
    tracked_request.stop_span()
    child2 = tracked_request.start_span(operation="child2")

    assert child2.ignore
    assert child2.ignore_children
    assert caplog.record_tuples == [
        (
            "scout_apm.core.tracked_request",
            logging.DEBUG,
            "Hit the maximum number of spans, this trace will be incomplete.",
        )
    ]


def test_span_captures_backtrace(tracked_request):
    span = tracked_request.start_span(operation="Sql/Work")
    # Pretend it was started 1 second ago
    span.start_time = dt.datetime.utcnow() - dt.timedelta(seconds=1)
    tracked_request.stop_span()
    assert "stack" in span.tags


def test_should_capture_backtrace_default_true(tracked_request):
    span = tracked_request.start_span(operation="Something")
    # Trigger 'slow' condition
    span.start_time -= dt.timedelta(seconds=2)

    tracked_request.stop_span()

    stack = span.tags["stack"]
    assert all(set(i.keys()) == {"file", "line", "function"} for i in stack)


def test_should_capture_backtrace_false(tracked_request):
    span = tracked_request.start_span("Something", should_capture_backtrace=False)
    # Trigger 'slow' condition
    span.start_time -= dt.timedelta(seconds=2)

    tracked_request.stop_span()

    assert "stack" not in span.tags


def test_extra_stop_span_is_ignored(tracked_request):
    tracked_request.stop_span()  # does not crash


def test_finish_does_not_capture_memory(tracked_request):
    tracked_request.finish()

    assert "mem_delta" not in tracked_request.tags


def test_finish_does_captures_memory_on_real_requests(tracked_request):
    tracked_request.is_real_request = True
    tracked_request.finish()

    assert "mem_delta" in tracked_request.tags


def test_finish_log_request_info(tracked_request, caplog):
    tracked_request.is_real_request = True
    tracked_request.start_span(operation="Something")
    tracked_request.stop_span()

    assert (
        "scout_apm.core.tracked_request",
        logging.DEBUG,
        "Stopping request: {}".format(tracked_request.request_id),
    ) in caplog.record_tuples

    assert (
        "scout_apm.core.tracked_request",
        logging.DEBUG,
        "Sending request: {}.".format(tracked_request.request_id),
    ) in caplog.record_tuples

    assert (
        "scout_apm.core.tracked_request",
        logging.DEBUG,
        (
            "Request {} ".format(tracked_request.request_id)
            + "start_time={} ".format(tracked_request.start_time)
            + "end_time={} ".format(tracked_request.end_time)
            + "duration={} ".format(
                (tracked_request.end_time - tracked_request.start_time).total_seconds()
            )
            + "active_spans=0 "
            + "complete_spans=1 "
            + "tags=1 "
            + "hit_max=False "
            + "is_real_request=True "
            + "sent=True"
        ),
    ) in caplog.record_tuples


def test_finish_log_request_info_with_logged_payload(
    tracked_request, caplog, reset_config
):
    scout_config.set(log_payload_content=True)
    tracked_request.is_real_request = True
    tracked_request.start_span(operation="Something")
    tracked_request.stop_span()

    # Find the logged message.
    actual_message = None
    for module, level, message in caplog.record_tuples:
        if module == "scout_apm.core.tracked_request" and level == logging.DEBUG:
            if message.startswith(
                "Sending request: {}. Payload: ".format(tracked_request.request_id)
            ):
                actual_message = message
                break
    assert actual_message
    # Verify the counts of the spans and the request id.
    assert actual_message.count("'StartRequest'") == 1
    assert actual_message.count("'FinishRequest'") == 1
    assert actual_message.count("'TagRequest'") == 1
    assert actual_message.count("'StartSpan'") == 1
    assert actual_message.count("'StopSpan'") == 1
    if objtrace.is_extension:
        assert actual_message.count("'TagSpan'") == 3
        total_requests = 8
    else:
        assert actual_message.count("'TagSpan'") == 0
        total_requests = 5
    # Verify each request id in the payload is the tracked request's.
    assert actual_message.count("'request_id'") == total_requests
    # The actual request id is also included in the log message after Sending request:
    assert actual_message.count(tracked_request.request_id) == total_requests + 1


def test_finish_clears_context():
    tracked_request_1 = TrackedRequest.instance()
    tracked_request_1.is_real_request = True
    tracked_request_2 = TrackedRequest.instance()
    try:
        assert tracked_request_2 is tracked_request_1
    finally:
        tracked_request_1.finish()
        tracked_request_2.finish()

    tracked_request_3 = TrackedRequest.instance()
    try:
        assert tracked_request_3 is not tracked_request_2
    finally:
        tracked_request_3.finish()


def test_is_ignored_default_false(tracked_request):
    assert not tracked_request.is_ignored()


def test_is_ignored_mark_true(tracked_request):
    tracked_request.tag("ignore_transaction", True)
    assert tracked_request.is_ignored()


def test_request_only_sent_once(tracked_request, caplog):
    tracked_request.is_real_request = True
    tracked_request.start_span(operation="Something")
    tracked_request.stop_span()

    assert tracked_request.sent

    sent_log = (
        "scout_apm.core.tracked_request",
        logging.DEBUG,
        "Sending request: {}.".format(tracked_request.request_id),
    )
    info_log = (
        "scout_apm.core.tracked_request",
        logging.DEBUG,
        (
            "Request {} ".format(tracked_request.request_id)
            + "start_time={} ".format(tracked_request.start_time)
            + "end_time={} ".format(tracked_request.end_time)
            + "duration={} ".format(
                (tracked_request.end_time - tracked_request.start_time).total_seconds()
            )
            + "active_spans=0 "
            + "complete_spans=1 "
            + "tags=1 "
            + "hit_max=False "
            + "is_real_request=True "
            + "sent=True"
        ),
    )
    assert (
        len([log_tuple for log_tuple in caplog.record_tuples if log_tuple == sent_log])
        == 1
    )
    assert (
        len([log_tuple for log_tuple in caplog.record_tuples if log_tuple == info_log])
        == 1
    )

    # Call finish again.
    tracked_request.finish()
    assert (
        len([log_tuple for log_tuple in caplog.record_tuples if log_tuple == sent_log])
        == 1
    )
    assert (
        len([log_tuple for log_tuple in caplog.record_tuples if log_tuple == info_log])
        == 2
    )
