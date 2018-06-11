from scout_apm.core.tracked_request import TrackedRequest


def test_instance():
    tr1 = TrackedRequest.instance()
    tr2 = TrackedRequest.instance()
    assert(tr1.req_id == tr2.req_id)
    assert(tr1 == tr2)


def test_tag_request():
    tr = TrackedRequest()

    tr.tag("foo", "bar")

    assert(len(tr.tags) == 1)
    assert(tr.tags['foo'] == 'bar')


def test_tag_span():
    tr = TrackedRequest()
    span = tr.start_span()
    span.tag("a", "b")
    tr.stop_span()

    assert(len(tr.complete_spans[0].tags) == 1)
    assert(tr.complete_spans[0].tags['a'] == 'b')


def test_start_span_wires_parents():
    tr = TrackedRequest()
    span1 = tr.start_span()
    span2 = tr.start_span()
    assert(span1.parent is None)
    assert(span2.parent == span1.span_id)
