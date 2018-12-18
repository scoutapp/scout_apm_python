# coding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

from scout_apm.api import (
    BackgroundTransaction,
    Config,
    Context,
    WebTransaction,
    ignore_transaction,
    instrument,
)
from scout_apm.core.tracked_request import TrackedRequest


def test_instrument_context_manager():
    # Save TR here, so it doesn't disappear on us when span finishes
    tr = TrackedRequest.instance()

    with instrument("Test ContextMgr") as inst:
        inst.tag("foo", "bar")

    span = tr.complete_spans[-1]
    assert span.operation == "Custom/Test ContextMgr"


def test_instrument_decorator():
    # Save TR here, so it doesn't disappear on us when span finishes
    tr = TrackedRequest.instance()

    @instrument("Test Decorator")
    def test():
        pass

    test()

    span = tr.complete_spans[-1]
    assert span.operation == "Custom/Test Decorator"


def test_instrument_context_manager_with_kind():
    # Save TR here, so it doesn't disappear on us when span finishes
    tr = TrackedRequest.instance()

    with instrument("Get", kind="Redis") as inst:
        inst.tag("foo", "bar")

    span = tr.complete_spans[-1]
    assert span.operation == "Redis/Get"


def test_instrument_decorator_with_kind():
    # Save TR here, so it doesn't disappear on us when span finishes
    tr = TrackedRequest.instance()

    @instrument("GET example.com", kind="HTTP")
    def test():
        pass

    test()

    span = tr.complete_spans[-1]
    assert span.operation == "HTTP/GET example.com"


def test_instrument_context_manager_default_tags():
    # Save TR here, so it doesn't disappear on us when span finishes
    tr = TrackedRequest.instance()

    with instrument("tag test", tags={"x": 99}):
        pass

    span = tr.complete_spans[-1]
    assert span.tags["x"] == 99


def test_instrument_decorator_default_tags():
    # Save TR here, so it doesn't disappear on us when span finishes
    tr = TrackedRequest.instance()

    @instrument("tag test", tags={"x": 99})
    def test():
        pass

    test()

    span = tr.complete_spans[-1]
    assert span.tags["x"] == 99


def test_instrument_non_ascii_params():
    # Save TR here, so it doesn't disappear on us when span finishes
    tr = TrackedRequest.instance()

    @instrument(operation="Faire le café", kind="Personnalisé")
    def make_coffee():
        pass

    make_coffee()

    span = tr.complete_spans[-1]
    assert span.operation == "Personnalisé/Faire le café"


def test_instrument_non_ascii_bytes_params():
    # Save TR here, so it doesn't disappear on us when span finishes
    tr = TrackedRequest.instance()

    # On Python 2, user code that doesn't enable unicode_literals may contain
    # non-ASCII bystrings. For writing a test that works across Python versions,
    # the easiest is to create bytestrings by encoding unicode strings.
    @instrument(
        operation="Faire le café".encode("utf-8"), kind="Personnalisé".encode("utf-8")
    )
    def make_coffee():
        pass

    make_coffee()

    span = tr.complete_spans[-1]
    assert span.operation == "Personnalisé/Faire le café"


def test_web_transaction_start_stop():
    tr = TrackedRequest.instance()

    WebTransaction.start("Foo")
    WebTransaction.stop()

    span = tr.complete_spans[-1]
    assert span.operation == "Controller/Foo"


def test_web_transaction_context_manager():
    tr = TrackedRequest.instance()
    x = 0

    with WebTransaction("Foo"):
        x = 1

    span = tr.complete_spans[-1]
    assert x == 1
    assert span.operation == "Controller/Foo"


def test_web_transaction_decorator():
    tr = TrackedRequest.instance()

    @WebTransaction("Bar")
    def my_transaction():
        pass

    my_transaction()

    span = tr.complete_spans[-1]
    assert span.operation == "Controller/Bar"


def test_web_transaction_non_ascii_params():
    tr = TrackedRequest.instance()

    @WebTransaction("Acheter du café")
    def buy_coffee():
        pass

    buy_coffee()

    span = tr.complete_spans[-1]
    assert span.operation == "Controller/Acheter du café"


def test_web_transaction_non_ascii_bytes_params():
    tr = TrackedRequest.instance()

    @WebTransaction("Acheter du café".encode("utf-8"))
    def buy_coffee():
        pass

    buy_coffee()

    span = tr.complete_spans[-1]
    assert span.operation == "Controller/Acheter du café"


def test_background_transaction_start_stop():
    tr = TrackedRequest.instance()

    BackgroundTransaction.start("Foo")
    BackgroundTransaction.stop()

    span = tr.complete_spans[-1]
    assert span.operation == "Job/Foo"


def test_background_transaction_context_manager():
    tr = TrackedRequest.instance()
    x = 0

    with BackgroundTransaction("Foo"):
        x = 1

    span = tr.complete_spans[-1]
    assert x == 1
    assert span.operation == "Job/Foo"


def test_background_transaction_decorator():
    tr = TrackedRequest.instance()

    @BackgroundTransaction("Bar")
    def my_transaction():
        pass

    my_transaction()

    span = tr.complete_spans[-1]
    assert span.operation == "Job/Bar"


def test_background_transaction_non_ascii_params():
    tr = TrackedRequest.instance()

    @BackgroundTransaction("Acheter du café")
    def buy_coffee():
        pass

    buy_coffee()

    span = tr.complete_spans[-1]
    assert span.operation == "Job/Acheter du café"


def test_background_transaction_non_ascii_bytes_params():
    tr = TrackedRequest.instance()

    @BackgroundTransaction("Acheter du café".encode("utf-8"))
    def buy_coffee():
        pass

    buy_coffee()

    span = tr.complete_spans[-1]
    assert span.operation == "Job/Acheter du café"


def test_context():
    # Save TR here, so it doesn't disappear on us when span finishes
    tr = TrackedRequest.instance()

    Context.add("x", 99)

    tr.finish()

    assert tr.tags["x"] == 99


def test_config():
    try:
        Config.set(revision_sha="4de21f8ea228a082d4f039c0c991ee41dfb6f9d8")
    finally:
        Config.reset_all()


def test_ignore_transaction():
    tr = TrackedRequest.instance()

    ignore_transaction()

    tr.finish()

    assert tr.tags["ignore_transaction"] == True
