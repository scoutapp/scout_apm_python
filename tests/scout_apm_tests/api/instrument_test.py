import scout_apm.api
from scout_apm.core.tracked_request import TrackedRequest


def test_context_manager_instrument():
    # Save TR here, so it doesn't disappear on us when span finishes
    tr = TrackedRequest.instance()

    with scout_apm.api.instrument("Test ContextMgr") as instrument:
        instrument.tag("foo", "bar")

    span = tr.complete_spans[-1]
    assert(span.operation == "Test ContextMgr")


def test_decoration_instrument():
    # Save TR here, so it doesn't disappear on us when span finishes
    tr = TrackedRequest.instance()

    @scout_apm.api.instrument("Test Decorator")
    def test():
        a = 1
    test()

    span = tr.complete_spans[-1]
    assert(span.operation == "Test Decorator")
