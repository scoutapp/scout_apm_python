# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import pytest

from scout_apm.api import (
    BackgroundTransaction,
    Config,
    Context,
    Error,
    WebTransaction,
    ignore_transaction,
    instrument,
    rename_transaction,
)
from scout_apm.core.config import scout_config


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


def test_instrument_decorator_method(tracked_request):
    class Example(object):
        @instrument("Test Decorator")
        def method(self):
            pass

    Example().method()

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Custom/Test Decorator"


def test_instrument_decorator_classmethod(tracked_request):
    class Example(object):
        @classmethod
        @instrument("Test Decorator")
        def method(cls):
            pass

    Example.method()

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Custom/Test Decorator"


def test_instrument_decorator_staticmethod(tracked_request):
    class Example(object):
        @staticmethod
        @instrument("Test Decorator")
        def method():
            pass

    Example.method()

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
    assert tracked_request.complete_spans[0].tags["x"] == 99


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
    sha = "4de21f8ea228a082d4f039c0c991ee41dfb6f9d8"
    try:
        Config.set(revision_sha=sha)
        assert scout_config.value("revision_sha") == sha
    finally:
        scout_config.reset_all()


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


def test_error_capture(error_monitor_errors, tracked_request):
    scout_config.set(errors_enabled=True)
    tracked_request.tag("spam", "eggs")

    request_path = "/test/"
    request_params = {"page": 1}
    session = {"step": 0}
    custom_controller = "test-controller"
    custom_params = {"foo": "bar"}
    try:
        try:
            1 / 0
        except ZeroDivisionError as exc:
            Error.capture(
                exc,
                request_path=request_path,
                request_params=request_params,
                session=session,
                custom_controller=custom_controller,
                custom_params=custom_params,
            )
    finally:
        scout_config.reset_all()

    assert len(error_monitor_errors) == 1
    error = error_monitor_errors[0]
    filepath, line, func_str = error["trace"][0].split(":")
    assert filepath.endswith("tests/integration/test_api.py")
    # The line number changes between python versions. Make sure it's not empty.
    assert line
    assert func_str == "in test_error_capture"
    assert error["exception_class"] == "ZeroDivisionError"
    assert error["message"] == "division by zero"
    assert error["context"] == {
        "spam": "eggs",
        "custom_params": {"foo": "bar"},
    }
    assert error["request_uri"] == request_path
    assert error["request_params"] == {"page": "1"}
    assert error["request_session"] == {"step": "0"}
    assert error["request_components"] == {
        "module": None,
        "controller": custom_controller,
        "action": None,
    }


@pytest.mark.parametrize(
    "value",
    [
        None,
        0,
        1,
        "foo",
        True,
    ],
)
def test_error_capture_skip(value, error_monitor_errors):
    scout_config.set(errors_enabled=True)

    try:
        Error.capture(value)
    finally:
        scout_config.reset_all()

    assert len(error_monitor_errors) == 0
