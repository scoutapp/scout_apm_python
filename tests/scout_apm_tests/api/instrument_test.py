import scout_apm.api
from scout_apm.core.tracked_request import TrackedRequest


def test_context_manager_instrument():
    # Save TR here, so it doesn't disappear on us when span finishes
    tr = TrackedRequest.instance()

    with scout_apm.api.instrument('Test ContextMgr') as instrument:
        instrument.tag('foo', 'bar')

    span = tr.complete_spans[-1]
    assert(span.operation == 'Custom/Test ContextMgr')


def test_decoration_instrument():
    # Save TR here, so it doesn't disappear on us when span finishes
    tr = TrackedRequest.instance()

    @scout_apm.api.instrument('Test Decorator')
    def test():
        a = 1
    test()

    span = tr.complete_spans[-1]
    assert(span.operation == 'Custom/Test Decorator')


def test_context_manager_instrument_with_kind():
    # Save TR here, so it doesn't disappear on us when span finishes
    tr = TrackedRequest.instance()

    with scout_apm.api.instrument('Get', kind='Redis') as instrument:
        instrument.tag('foo', 'bar')

    span = tr.complete_spans[-1]
    assert(span.operation == 'Redis/Get')


def test_decoration_instrument_with_kind():
    # Save TR here, so it doesn't disappear on us when span finishes
    tr = TrackedRequest.instance()

    @scout_apm.api.instrument('GET example.com', kind='HTTP')
    def test():
        a = 1
    test()

    span = tr.complete_spans[-1]
    assert(span.operation == 'HTTP/GET example.com')


def test_context_manager_default_tags():
    # Save TR here, so it doesn't disappear on us when span finishes
    tr = TrackedRequest.instance()

    with scout_apm.api.instrument('tag test', tags={'x': 99}):
        a = 1

    span = tr.complete_spans[-1]
    assert(len(span.tags) == 1)
    assert(span.tags['x'] == 99)


def test_decoration_default_tags():
    # Save TR here, so it doesn't disappear on us when span finishes
    tr = TrackedRequest.instance()

    @scout_apm.api.instrument('tag test', tags={'x': 99})
    def test():
        a = 1
    test()

    span = tr.complete_spans[-1]
    assert(len(span.tags) == 1)
    assert(span.tags['x'] == 99)
