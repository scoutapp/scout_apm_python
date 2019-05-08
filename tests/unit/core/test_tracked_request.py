# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import datetime, timedelta

import pytest

from scout_apm.core.tracked_request import TrackedRequest

try:
    from scout_apm.core import objtrace
except ImportError:
    objtrace = None


@pytest.fixture
def tr():
    request = TrackedRequest()
    try:
        yield request
    finally:
        request.finish()


def test_tracked_request_instance_is_a_singleton():
    tr1 = TrackedRequest.instance()
    tr2 = TrackedRequest.instance()
    try:
        assert tr2 is tr1
    finally:
        tr1.finish()
        tr2.finish()


def test_real_request(tr):
    assert not tr.is_real_request()
    tr.mark_real_request()
    assert tr.is_real_request()


def test_tag_request(tr):

    tr.tag("foo", "bar")

    assert len(tr.tags) == 1
    assert tr.tags["foo"] == "bar"


def test_tag_request_overwrite(tr):

    tr.tag("foo", "bar")
    tr.tag("foo", "baz")

    assert len(tr.tags) == 1
    assert tr.tags["foo"] == "baz"


def test_tag_span(tr):
    span = tr.start_span()
    span.tag("foo", "bar")
    tr.stop_span()

    assert tr.complete_spans[0].tags["foo"] == "bar"


def test_tag_span_overwrite(tr):
    span = tr.start_span()
    span.tag("foo", "bar")
    span.tag("foo", "baz")
    tr.stop_span()

    assert tr.complete_spans[0].tags["foo"] == "baz"


def test_start_span_wires_parents(tr):
    span1 = tr.start_span()
    span2 = tr.start_span()
    assert span1.parent is None
    assert span2.parent == span1.span_id


@pytest.mark.skipif(objtrace is None, reason="objtrace extension isn't available")
def test_tags_allocations_for_spans(tr):
    span = tr.start_span()
    tr.stop_span()
    assert span.tags["allocations"] > 0


def test_start_span_does_not_ignore_children(tr):
    tr.start_span(operation="parent")
    child1 = tr.start_span()
    assert not child1.ignore
    assert not child1.ignore_children
    child2 = tr.start_span()
    assert not child2.ignore
    assert not child2.ignore_children
    tr.stop_span()
    tr.stop_span()
    tr.stop_span()
    assert 3 == len(tr.complete_spans)
    assert "parent" == tr.complete_spans[2].operation


def test_start_span_ignores_children(tr):
    tr.start_span(operation="parent", ignore_children=True)
    child1 = tr.start_span()
    assert child1.ignore
    assert child1.ignore_children
    child2 = tr.start_span()
    assert child2.ignore
    assert child2.ignore_children
    tr.stop_span()
    tr.stop_span()
    tr.stop_span()
    assert 1 == len(tr.complete_spans)
    assert "parent" == tr.complete_spans[0].operation


def test_span_captures_backtrace(tr):
    span = tr.start_span(
        operation="Sql/Work", start_time=datetime.utcnow() - timedelta(seconds=1)
    )
    tr.stop_span()
    assert span.tags["stack"]


def test_span_does_not_capture_backtrace(tr):
    controller = tr.start_span(
        operation="Controller/Work",
        start_time=datetime.utcnow() - timedelta(seconds=10),
    )
    middleware = tr.start_span(
        operation="Middleware/Work",
        start_time=datetime.utcnow() - timedelta(seconds=10),
    )
    tr.stop_span()
    tr.stop_span()
    assert "stack" not in controller.tags
    assert "stack" not in middleware.tags


def test_extra_stop_span_is_ignored(tr):
    tr.stop_span()  # does not crash


def test_finish_does_not_capture_memory(tr):
    tr.finish()

    assert "mem_delta" not in tr.tags


def test_finish_does_captures_memory_on_real_requests(tr):
    tr.mark_real_request()
    tr.finish()

    assert "mem_delta" in tr.tags


def test_is_ignored(tr):
    assert not tr.is_ignored()
    tr.tag("ignore_transaction", True)
    assert tr.is_ignored()
