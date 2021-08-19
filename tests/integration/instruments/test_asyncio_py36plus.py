# coding=utf-8
"""While asyncio isn't instrumented specifically, it's good to verify
the functionality is instrumented.

Note, the tracked_request fixture should not be used as the running
thread may change from when the fixture is started to when the tests
run. This is only a problem on python 3.6 and results in getting the
tracked_instance in the test itself.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import asyncio
import contextvars
import functools
import sys

import pytest

from scout_apm.api import BackgroundTransaction, instrument
from scout_apm.core.tracked_request import TrackedRequest


def create_task(coro):
    """Provide interface to create_task regardless of python version."""
    if hasattr(asyncio, "create_task"):  # py37+
        return asyncio.create_task(coro)
    return asyncio.get_event_loop().create_task(coro)


async def coro(value=None, wait=None):
    """Helper function for testing coroutines.

    :value: This will be inserted into the ``tags`` of ``instrument``.
    :wait: A float of seconds to be waited before calling ``instrument``.
    :loop: EventLoop to be used if any.
    :returns: nothing.
    """
    if wait:
        await asyncio.sleep(wait)
    tags = {"value": value} if value else None
    with instrument("coro", tags=tags):
        await asyncio.sleep(0.1)


def get_future():
    """Helper function to return a future for the current event loop."""
    if hasattr(asyncio, "get_running_loop"):  # py37+
        return asyncio.get_running_loop().create_future()
    return asyncio.get_event_loop().create_future()


async def set_future(fut, wait):
    """Helper function to set a future after a set delay.

    :fut: The future to be set.
    :wait: A float of seconds to be waited.
    :returns: nothing.
    """
    await asyncio.sleep(wait)
    with instrument("set_future"):
        fut.set_result("complete")


async def resolving_future(wait):
    """Get a future that will resolve eventually."""
    fut = get_future()
    create_task(set_future(fut, wait=wait))
    return fut


@pytest.mark.asyncio
async def test_coroutine(tracked_requests, tracked_request):
    with BackgroundTransaction("test"):
        await coro()

    assert len(tracked_request.complete_spans) == 2
    span = tracked_request.complete_spans[0]
    assert span.operation == "Custom/coro"
    assert tracked_request.complete_spans[1].operation == "Job/test"
    assert len(tracked_requests) == 1
    assert tracked_requests[0].request_id == tracked_request.request_id


@pytest.mark.asyncio
async def test_coroutine_timeout(tracked_requests, tracked_request):
    with BackgroundTransaction("test"):
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(coro("long", wait=0.5), timeout=0.1)

    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Job/test"
    assert len(tracked_requests) == 1
    assert tracked_requests[0].request_id == tracked_request.request_id


@pytest.mark.asyncio
async def test_task_awaited(tracked_requests, tracked_request):
    with BackgroundTransaction("test"):
        await create_task(coro())

    assert len(tracked_request.complete_spans) == 2
    span = tracked_request.complete_spans[0]
    assert span.operation == "Custom/coro"
    assert tracked_request.complete_spans[1].operation == "Job/test"
    assert len(tracked_requests) == 1
    assert tracked_requests[0].request_id == tracked_request.request_id


@pytest.mark.asyncio
async def test_nested_tasks(tracked_requests, tracked_request):
    @instrument.async_("orchestrator")
    async def orchestrator():
        await coro("1")
        await asyncio.gather(
            # Force this coroutine to finish later for idempotency
            coro("2a", wait=0.5),
            coro("2b"),
        )

    with BackgroundTransaction("test"):
        await orchestrator()

    spans = tracked_request.complete_spans
    assert len(spans) == 5
    assert [span.operation for span in spans] == [
        "Custom/coro",
        "Custom/coro",
        "Custom/coro",
        "Custom/orchestrator",
        "Job/test",
    ]
    # Verify the order of the coroutines
    assert [span.tags.get("value") for span in spans] == [
        "1",
        "2b",
        "2a",
        None,
        None,
    ]
    assert len(tracked_requests) == 1
    assert tracked_requests[0].request_id == tracked_request.request_id


@pytest.mark.asyncio
async def test_task_not_awaited(tracked_requests, tracked_request):
    with BackgroundTransaction("test"):
        await create_task(coro("short"))
        long = create_task(coro("long", wait=0.5))

    assert len(tracked_requests) == 1
    assert len(tracked_request.complete_spans) == 2
    span = tracked_request.complete_spans[0]
    assert span.operation == "Custom/coro"
    assert span.tags["value"] == "short"
    assert tracked_request.complete_spans[1].operation == "Job/test"

    assert not long.done()
    await long
    assert tracked_request.complete_spans[0].tags["value"] == "short"
    assert tracked_request.complete_spans[1].operation == "Job/test"

    assert tracked_requests[0].request_id == tracked_request.request_id

    if sys.version_info[:2] < (3, 7):
        # Python 3.6 utilizes the contextvars backport which functions
        # slightly differently than the contextvars stdlib implementation
        # in 3.7+
        assert len(tracked_request.complete_spans) == 2
        assert len(tracked_requests) == 1
    else:
        assert len(tracked_request.complete_spans) == 3
        assert tracked_request.complete_spans[2].tags["value"] == "long"
        # When we await long, it will call finish again which adds it
        # to tracked_requests
        assert len(tracked_requests) == 2
        assert tracked_requests[0] is tracked_requests[1]


@pytest.mark.asyncio
async def test_task_cancelled(tracked_requests, tracked_request):
    with BackgroundTransaction("test"):
        long = create_task(coro("long", wait=0.5))
        long.cancel()

    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Job/test"
    assert len(tracked_requests) == 1
    assert tracked_requests[0].request_id == tracked_request.request_id


@pytest.mark.asyncio
async def test_future_awaited(tracked_requests, tracked_request):
    with BackgroundTransaction("test"):
        fut = get_future()
        create_task(set_future(fut, wait=0.5))
        await fut
        assert len(tracked_request.complete_spans) == 1
        assert tracked_request.complete_spans[0].operation == "Custom/set_future"

    assert len(tracked_request.complete_spans) == 2
    assert tracked_request.complete_spans[1].operation == "Job/test"
    assert len(tracked_requests) == 1
    assert tracked_requests[0].request_id == tracked_request.request_id


@pytest.mark.asyncio
async def test_future_gathered(tracked_requests, tracked_request):
    with BackgroundTransaction("test"):
        await asyncio.gather(
            resolving_future(0.5),
            coro(wait=0.5),
        )
        assert len(tracked_request.complete_spans) == 2
        # gather can run the coroutines/futures in any order.
        operations = {span.operation for span in tracked_request.complete_spans}
        assert operations == {"Custom/set_future", "Custom/coro"}

    assert len(tracked_request.complete_spans) == 3
    assert tracked_request.complete_spans[2].operation == "Job/test"
    assert len(tracked_requests) == 1
    assert tracked_requests[0].request_id == tracked_request.request_id


@pytest.mark.asyncio
async def test_future_not_gathered(tracked_requests, tracked_request):
    with BackgroundTransaction("test"):
        gather_future = asyncio.gather(
            resolving_future(0.5),
            coro(wait=0.5),
            coro(wait=0.5),
            coro(wait=0.5),
        )

    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Job/test"

    await gather_future

    if sys.version_info[:2] < (3, 7):
        # Python 3.6 utilizes the contextvars backport which functions
        # slightly differently than the contextvars stdlib implementation
        # in 3.7+
        assert len(tracked_request.complete_spans) == 1
        assert len(tracked_requests) == 1
    else:
        assert len(tracked_request.complete_spans) == 5
        # When the last awaitable completes, it will call finish again which
        # adds it to tracked_requests
        assert len(tracked_requests) == 2
        assert tracked_requests[0].request_id == tracked_request.request_id


@pytest.mark.asyncio
async def test_future_cancelled(tracked_requests, tracked_request):
    with BackgroundTransaction("test"):
        gather_future = asyncio.gather(
            resolving_future(0.5),
            coro(wait=0.5),
        )
        gather_future.cancel()

    assert len(tracked_requests) == 1
    assert tracked_requests[0].request_id == tracked_request.request_id
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Job/test"


@pytest.mark.asyncio
async def test_run_in_executor_with_context_copied(tracked_requests, tracked_request):
    def inner_func():
        with BackgroundTransaction("test"):
            pass

    loop = asyncio.get_event_loop()
    child = functools.partial(inner_func)
    context = contextvars.copy_context()
    func = context.run
    args = (child,)
    await loop.run_in_executor(None, func, *args)

    assert len(tracked_requests) == 1
    assert tracked_requests[0].request_id == tracked_request.request_id
    assert len(tracked_requests[0].complete_spans) == 1


@pytest.mark.asyncio
async def test_run_in_executor_with_context_copied_and_active_span(
    tracked_requests, tracked_request
):
    # Start an outer span to prevent the tracked_request from finishing.
    tracked_request.start_span("outer")

    def inner_func():
        with BackgroundTransaction("test"):
            pass

    # Run inner_func
    loop = asyncio.get_event_loop()
    child = functools.partial(inner_func)
    context = contextvars.copy_context()
    func = context.run
    args = (child,)
    await loop.run_in_executor(None, func, *args)
    # Verify finish wasn't called
    assert len(tracked_requests) == 0
    assert len(tracked_request.complete_spans) == 1

    tracked_request.stop_span()

    assert tracked_requests[0].request_id == tracked_request.request_id
    assert len(tracked_requests[0].complete_spans) == 2


@pytest.mark.asyncio
async def test_run_in_executor_with_context_copied_escalates_ignored(tracked_request):
    # Start an outer span to prevent the tracked_request from finishing.
    tracked_request.start_span("outer")

    def inner_func():
        with BackgroundTransaction("test"):
            TrackedRequest.instance().tag("ignore_transaction", True)

    # Run inner_func
    loop = asyncio.get_event_loop()
    child = functools.partial(inner_func)
    context = contextvars.copy_context()
    func = context.run
    args = (child,)
    await loop.run_in_executor(None, func, *args)
    tracked_request.stop_span()
    assert tracked_request.is_ignored()


@pytest.mark.asyncio
async def test_run_in_executor_without_context_copied(
    tracked_requests, tracked_request
):
    def inner_func():
        with BackgroundTransaction("test"):
            pass

    loop = asyncio.get_event_loop()
    func = functools.partial(inner_func)
    await loop.run_in_executor(None, func)

    assert len(tracked_requests) == 1
    assert tracked_requests[0].request_id != tracked_request.request_id
    assert len(tracked_requests[0].complete_spans) == 1


@pytest.mark.asyncio
async def test_run_in_executor_without_context_copied_and_active_span(
    tracked_requests, tracked_request
):
    # Start an outer span to prevent the tracked_request from finishing.
    tracked_request.start_span("outer")

    def inner_func():
        with BackgroundTransaction("test"):
            pass

    # Run inner_func
    loop = asyncio.get_event_loop()
    func = functools.partial(inner_func)
    await loop.run_in_executor(None, func)
    # Verify finish wasn't called
    assert len(tracked_requests) == 1
    assert len(tracked_requests[0].complete_spans) == 1
    assert len(tracked_request.complete_spans) == 0

    tracked_request.stop_span()

    assert tracked_requests[0].request_id != tracked_request.request_id
    assert len(tracked_request.complete_spans) == 1


@pytest.mark.asyncio
async def test_run_in_executor_without_context_copied_escalates_ignored(
    tracked_request,
):
    # Start an outer span to prevent the tracked_request from finishing.
    tracked_request.start_span("outer")

    def inner_func():
        with BackgroundTransaction("test"):
            TrackedRequest.instance().tag("ignore_transaction", True)

    # Run inner_func
    loop = asyncio.get_event_loop()
    func = functools.partial(inner_func)
    await loop.run_in_executor(None, func)

    tracked_request.stop_span()

    assert not tracked_request.is_ignored()
