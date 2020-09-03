# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime as dt
import logging
import sys

from scout_apm.core import objtrace
from scout_apm.core.tracked_request import TrackedRequest
from tests.compat import mock
from tests.tools import skip_if_objtrace_is_extension, skip_if_objtrace_not_extension


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
    if sys.version_info[0] == 2:
        assert "operation=u'myoperation'" in repr_
    else:
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
            logging.WARNING,
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


def test_is_ignored_default_false(tracked_request):
    assert not tracked_request.is_ignored()


def test_is_ignored_mark_true(tracked_request):
    tracked_request.tag("ignore_transaction", True)
    assert tracked_request.is_ignored()
