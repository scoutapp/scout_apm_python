from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import datetime, timedelta

from scout_apm.core.tracked_request import TrackedRequest

try:
    from scout_apm.core import objtrace  # noqa: F401

    HAS_OBJTRACE = True
except ImportError:
    HAS_OBJTRACE = False


def test_instance():
    tr1 = TrackedRequest.instance()
    tr2 = TrackedRequest.instance()
    assert tr1.req_id == tr2.req_id
    assert tr1 == tr2


def test_tag_request():
    tr = TrackedRequest()

    tr.tag("foo", "bar")

    assert len(tr.tags) == 1
    assert tr.tags["foo"] == "bar"


def test_tag_span():
    tr = TrackedRequest()
    span = tr.start_span()
    span.tag("a", "b")
    tr.stop_span()

    assert tr.complete_spans[0].tags["a"] == "b"


def test_start_span_wires_parents():
    tr = TrackedRequest()
    span1 = tr.start_span()
    span2 = tr.start_span()
    assert span1.parent is None
    assert span2.parent == span1.span_id


def test_tags_allocations_for_spans():
    if HAS_OBJTRACE:
        tr = TrackedRequest()
        span = tr.start_span()
        tr.stop_span()
        assert span.tags["allocations"] > 0


def test_start_span_does_not_ignore_children():
    tr = TrackedRequest()
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


def test_start_span_ignores_children():
    tr = TrackedRequest()
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


def test_span_captures_backtrace():
    tr = TrackedRequest()
    span = tr.start_span(
        operation="Sql/Work", start_time=datetime.utcnow() - timedelta(seconds=1)
    )
    tr.stop_span()
    assert span.tags["stack"]


def test_span_does_not_capture_backtrace():
    tr = TrackedRequest()
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
