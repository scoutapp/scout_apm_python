# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from scout_apm.api import (
    BackgroundTransaction,
    Config,
    Context,
    WebTransaction,
    ignore_transaction,
    instrument,
    rename_transaction,
)


def test_instrument_context_manager(tracked_request):
    with instrument("Test ContextMgr") as inst:
        inst.tag("foo", "bar")

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Custom/Test ContextMgr"


def test_instrument_decorator(tracked_request):
    @instrument("Test Decorator")
    def example():
        pass

    example()

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Custom/Test Decorator"


def test_instrument_context_manager_with_kind(tracked_request):
    with instrument("Get", kind="Redis") as inst:
        inst.tag("foo", "bar")

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Redis/Get"


def test_instrument_decorator_with_kind(tracked_request):
    @instrument("GET example.com", kind="HTTP")
    def example():
        pass

    example()

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "HTTP/GET example.com"


def test_instrument_context_manager_default_tags(tracked_request):
    with instrument("tag test", tags={"x": 99}):
        pass

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].tags["x"] == 99


def test_instrument_decorator_default_tags(tracked_request):
    @instrument("tag test", tags={"x": 99})
    def example():
        pass

    example()

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].tags == {"x": 99}


def test_instrument_non_ascii_params(tracked_request):
    @instrument(operation="Faire le café", kind="Personnalisé")
    def make_coffee():
        pass

    make_coffee()

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Personnalisé/Faire le café"


def test_instrument_non_ascii_bytes_params(tracked_request):
    # On Python 2, user code that doesn't enable unicode_literals may contain
    # non-ASCII bystrings. For writing a test that works across Python versions,
    # the easiest is to create bytestrings by encoding unicode strings.
    @instrument(
        operation="Faire le café".encode("utf-8"), kind="Personnalisé".encode("utf-8")
    )
    def make_coffee():
        pass

    make_coffee()

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Personnalisé/Faire le café"


def test_web_transaction_start_stop(tracked_request):
    WebTransaction.start("Foo")
    WebTransaction.stop()

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Controller/Foo"


def test_web_transaction_context_manager(tracked_request):
    x = 0

    with WebTransaction("Foo"):
        x = 1

    assert x == 1
    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Controller/Foo"


def test_web_transaction_decorator(tracked_request):
    @WebTransaction("Bar")
    def my_transaction():
        pass

    my_transaction()

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Controller/Bar"


def test_web_transaction_default_tags(tracked_request):
    @WebTransaction("Bar", tags={"x": 99})
    def my_transaction():
        pass

    my_transaction()

    assert tracked_request.tags["x"] == 99


def test_web_transaction_non_ascii_params(tracked_request):
    @WebTransaction("Acheter du café")
    def buy_coffee():
        pass

    buy_coffee()

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Controller/Acheter du café"


def test_web_transaction_non_ascii_bytes_params(tracked_request):
    @WebTransaction("Acheter du café".encode("utf-8"))
    def buy_coffee():
        pass

    buy_coffee()

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Controller/Acheter du café"


def test_background_transaction_start_stop(tracked_request):
    BackgroundTransaction.start("Foo")
    BackgroundTransaction.stop()

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Job/Foo"


def test_background_transaction_context_manager(tracked_request):
    x = 0

    with BackgroundTransaction("Foo"):
        x = 1

    assert x == 1
    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Job/Foo"


def test_background_transaction_decorator(tracked_request):
    @BackgroundTransaction("Bar")
    def my_transaction():
        pass

    my_transaction()

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Job/Bar"


def test_background_transaction_default_tags(tracked_request):
    @BackgroundTransaction("Bar", tags={"x": 99})
    def my_transaction():
        pass

    my_transaction()

    assert tracked_request.tags["x"] == 99


def test_background_transaction_non_ascii_params(tracked_request):
    @BackgroundTransaction("Acheter du café")
    def buy_coffee():
        pass

    buy_coffee()

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Job/Acheter du café"


def test_background_transaction_non_ascii_bytes_params(tracked_request):
    @BackgroundTransaction("Acheter du café".encode("utf-8"))
    def buy_coffee():
        pass

    buy_coffee()

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Job/Acheter du café"


def test_context(tracked_request):
    Context.add("x", 99)

    assert tracked_request.tags["x"] == 99


def test_config():
    try:
        Config.set(revision_sha="4de21f8ea228a082d4f039c0c991ee41dfb6f9d8")
    finally:
        Config.reset_all()


def test_ignore_transaction(tracked_request):
    ignore_transaction()

    assert tracked_request.tags["ignore_transaction"]


def test_rename_transaction(tracked_request):
    assert "transaction.name" not in tracked_request.tags

    rename_transaction("Unit Test")

    assert tracked_request.tags["transaction.name"] == "Unit Test"


def test_rename_transaction_none(tracked_request):
    assert "transaction.name" not in tracked_request.tags

    rename_transaction(None)

    assert "transaction.name" not in tracked_request.tags
