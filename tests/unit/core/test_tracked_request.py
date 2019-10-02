# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime as dt

import pytest

from scout_apm.core.tracked_request import TrackedRequest

try:
    from scout_apm.core import objtrace
except ImportError:
    objtrace = None


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
    assert not tracked_request.is_real_request()


def test_is_real_request_marked(tracked_request):
    tracked_request.mark_real_request()
    assert tracked_request.is_real_request()


def test_tag_request(tracked_request):
    tracked_request.tag("foo", "bar")
    assert tracked_request.tags == {"foo": "bar"}


def test_tag_request_overwrite(tracked_request):
    tracked_request.tag("foo", "bar")
    tracked_request.tag("foo", "baz")

    assert tracked_request.tags == {"foo": "baz"}


def test_span_repr(tracked_request):
    span = tracked_request.start_span()
    try:
        assert repr(span).startswith("<Span(")
    finally:
        tracked_request.stop_span()


def test_tag_span(tracked_request):
    span = tracked_request.start_span()
    span.tag("foo", "bar")
    tracked_request.stop_span()

    assert tracked_request.complete_spans[0].tags["foo"] == "bar"


def test_tag_span_overwrite(tracked_request):
    span = tracked_request.start_span()
    span.tag("foo", "bar")
    span.tag("foo", "baz")
    tracked_request.stop_span()

    assert tracked_request.complete_spans[0].tags["foo"] == "baz"


def test_start_span_wires_parents(tracked_request):
    span1 = tracked_request.start_span()
    span2 = tracked_request.start_span()
    assert span1.parent is None
    assert span2.parent == span1.span_id


@pytest.mark.skipif(objtrace is None, reason="objtrace extension isn't available")
def test_tags_allocations_for_spans(tracked_request):
    objtrace.enable()
    span = tracked_request.start_span()
    tracked_request.stop_span()
    assert span.tags["allocations"] > 0


def test_start_span_does_not_ignore_children(tracked_request):
    tracked_request.start_span(operation="parent")
    child1 = tracked_request.start_span()
    assert not child1.ignore
    assert not child1.ignore_children
    child2 = tracked_request.start_span()
    assert not child2.ignore
    assert not child2.ignore_children
    tracked_request.stop_span()
    tracked_request.stop_span()
    tracked_request.stop_span()
    assert len(tracked_request.complete_spans) == 3
    assert tracked_request.complete_spans[2].operation == "parent"


def test_start_span_ignores_children(tracked_request):
    tracked_request.start_span(operation="parent", ignore_children=True)
    child1 = tracked_request.start_span()
    assert child1.ignore
    assert child1.ignore_children
    child2 = tracked_request.start_span()
    assert child2.ignore
    assert child2.ignore_children
    tracked_request.stop_span()
    tracked_request.stop_span()
    tracked_request.stop_span()
    assert 1 == len(tracked_request.complete_spans)
    assert "parent" == tracked_request.complete_spans[0].operation


def test_span_captures_backtrace(tracked_request):
    span = tracked_request.start_span(operation="Sql/Work")
    # Pretend it was started 1 second ago
    span.start_time = dt.datetime.utcnow() - dt.timedelta(seconds=1)
    tracked_request.stop_span()
    assert "stack" in span.tags


def test_span_does_not_capture_backtrace(tracked_request):
    controller = tracked_request.start_span(operation="Controller/Work")
    middleware = tracked_request.start_span(operation="Middleware/Work")
    tracked_request.stop_span()
    tracked_request.stop_span()
    assert "stack" not in controller.tags
    assert "stack" not in middleware.tags


def test_extra_stop_span_is_ignored(tracked_request):
    tracked_request.stop_span()  # does not crash


def test_finish_does_not_capture_memory(tracked_request):
    tracked_request.finish()

    assert "mem_delta" not in tracked_request.tags


def test_finish_does_captures_memory_on_real_requests(tracked_request):
    tracked_request.mark_real_request()
    tracked_request.finish()

    assert "mem_delta" in tracked_request.tags


def test_is_ignored_default_false(tracked_request):
    assert not tracked_request.is_ignored()


def test_is_ignored_mark_true(tracked_request):
    tracked_request.tag("ignore_transaction", True)
    assert tracked_request.is_ignored()
