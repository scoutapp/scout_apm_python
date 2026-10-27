# coding=utf-8

import pytest

from scout_apm.api import BackgroundTransaction, WebTransaction, instrument
from tests.tools import (
    skip_if_context_decorator_wraps_coroutines,
    skip_unless_context_decorator_wraps_coroutines,
)


@pytest.mark.asyncio
async def test_instrument_decorator_async(tracked_request):
    @instrument.async_("Foo")
    async def foo():
        pass

    @instrument.async_("Bar")
    async def example():
        await foo()

    await example()

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 2
    assert tracked_request.complete_spans[0].operation == "Custom/Foo"
    assert tracked_request.complete_spans[1].operation == "Custom/Bar"


def test_instrument_decorator_async_for_sync_function(tracked_request):
    @instrument.async_("Bar")
    def example():
        pass

    with pytest.warns(RuntimeWarning):
        example()

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 0


@skip_if_context_decorator_wraps_coroutines
@pytest.mark.asyncio
async def test_instrument_decorator_async_misconfigured(tracked_request):
    """
    Test case where .async_ isn't used from parent instrument.
    Only misbehaves on Python < 3.15.
    """

    @instrument.async_("Foo")
    async def foo():
        pass

    @instrument("Bar")
    async def example():
        await foo()

    await example()

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Custom/Bar"


@skip_unless_context_decorator_wraps_coroutines
@pytest.mark.asyncio
async def test_instrument_decorator_async_without_async_(tracked_request):
    """On Python 3.15+, instrument works on async functions without .async_"""

    @instrument.async_("Foo")
    async def foo():
        pass

    @instrument("Bar")
    async def example():
        await foo()

    await example()

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 2
    assert tracked_request.complete_spans[0].operation == "Custom/Foo"
    assert tracked_request.complete_spans[1].operation == "Custom/Bar"


@pytest.mark.asyncio
async def test_instrument_decorator_async_classmethod(tracked_request):
    class Example(object):
        @classmethod
        @instrument.async_("Test Decorator")
        async def method(cls):
            pass

    await Example.method()

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Custom/Test Decorator"


@pytest.mark.asyncio
async def test_instrument_decorator_async_staticmethod(tracked_request):
    class Example(object):
        @staticmethod
        @instrument.async_("Test Decorator")
        async def method():
            pass

    await Example.method()

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Custom/Test Decorator"


@pytest.mark.asyncio
async def test_instrument_decorator_async_return_awaitable(tracked_request):
    @instrument.async_("Foo")
    async def foo():
        pass

    @instrument.async_("Bar")
    def return_awaitable():
        return foo()

    await return_awaitable()

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 2
    assert tracked_request.complete_spans[0].operation == "Custom/Foo"
    assert tracked_request.complete_spans[1].operation == "Custom/Bar"


@pytest.mark.asyncio
async def test_instrument_decorator_async_return_awaitable_misconfigured(
    tracked_request,
):
    """Test case where .async_ isn't used from parent instrument"""

    @instrument.async_("Foo")
    async def foo():
        pass

    @instrument("Bar")
    def return_awaitable():
        return foo()

    await return_awaitable()

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Custom/Bar"


@pytest.mark.asyncio
async def test_instrument_context_manager_async_await_later(tracked_request):
    """
    Test proving that if an awaitable goes unawaited in a context manager,
    the spans are lost.
    """

    @instrument.async_("Outer")
    async def foo():
        with instrument("Inner"):
            pass

    async def example():
        await foo()

    with instrument("Test Decorator"):
        awaitable = example()

    await awaitable

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Custom/Test Decorator"


@pytest.mark.asyncio
async def test_web_transaction_decorator_async(tracked_request):
    @instrument.async_("Foo")
    async def foo():
        pass

    @WebTransaction.async_("Bar")
    async def my_transaction():
        await foo()

    await my_transaction()

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 2
    assert tracked_request.complete_spans[0].operation == "Custom/Foo"
    assert tracked_request.complete_spans[1].operation == "Controller/Bar"
    assert tracked_request.operation == "Controller/Bar"


@skip_if_context_decorator_wraps_coroutines
@pytest.mark.asyncio
async def test_web_transaction_decorator_async_misconfigured(tracked_request):
    """
    Test case where .async_ isn't used from WebTransaction.
    Only misbehaves on Python < 3.15.
    """

    @instrument.async_("Foo")
    async def foo():
        pass

    @WebTransaction("Bar")
    async def my_transaction():
        await foo()

    await my_transaction()

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Controller/Bar"
    assert tracked_request.operation == "Controller/Bar"


@skip_unless_context_decorator_wraps_coroutines
@pytest.mark.asyncio
async def test_web_transaction_decorator_async_without_async_(tracked_request):
    """On Python 3.15+, WebTransaction works on async functions without .async_"""

    @instrument.async_("Foo")
    async def foo():
        pass

    @WebTransaction("Bar")
    async def my_transaction():
        await foo()

    await my_transaction()

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 2
    assert tracked_request.complete_spans[0].operation == "Custom/Foo"
    assert tracked_request.complete_spans[1].operation == "Controller/Bar"
    assert tracked_request.operation == "Controller/Bar"


def test_web_transaction_decorator_async_for_sync_function(tracked_request):
    @WebTransaction.async_("Bar")
    def example():
        pass

    with pytest.warns(RuntimeWarning):
        example()

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 0


@pytest.mark.asyncio
async def test_background_transaction_decorator_async(tracked_request):
    @instrument.async_("Foo")
    async def foo():
        pass

    @BackgroundTransaction.async_("Bar")
    async def my_transaction():
        await foo()

    await my_transaction()

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 2
    assert tracked_request.complete_spans[0].operation == "Custom/Foo"
    assert tracked_request.complete_spans[1].operation == "Job/Bar"
    assert tracked_request.operation == "Job/Bar"


@skip_if_context_decorator_wraps_coroutines
@pytest.mark.asyncio
async def test_background_transaction_decorator_async_misconfigured(tracked_request):
    """
    Test case where .async_ isn't used from BackgroundTransaction.
    Only misbehaves on Python < 3.15.
    """

    @instrument.async_("Foo")
    async def foo():
        pass

    @BackgroundTransaction("Bar")
    async def my_transaction():
        await foo()

    await my_transaction()

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Job/Bar"
    assert tracked_request.operation == "Job/Bar"


@skip_unless_context_decorator_wraps_coroutines
@pytest.mark.asyncio
async def test_background_transaction_decorator_async_without_async_(tracked_request):
    """
    On Python 3.15+, BackgroundTransaction works on async functions without .async_
    """

    @instrument.async_("Foo")
    async def foo():
        pass

    @BackgroundTransaction("Bar")
    async def my_transaction():
        await foo()

    await my_transaction()

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 2
    assert tracked_request.complete_spans[0].operation == "Custom/Foo"
    assert tracked_request.complete_spans[1].operation == "Job/Bar"
    assert tracked_request.operation == "Job/Bar"


def test_background_transaction_decorator_async_for_sync_function(tracked_request):
    @BackgroundTransaction.async_("Bar")
    def example():
        pass

    with pytest.warns(RuntimeWarning):
        example()

    assert len(tracked_request.active_spans) == 0
    assert len(tracked_request.complete_spans) == 0
