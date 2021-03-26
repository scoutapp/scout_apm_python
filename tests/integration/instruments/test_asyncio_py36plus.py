# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import asyncio
import logging

import pytest

from scout_apm.api import BackgroundTransaction, instrument
from scout_apm.instruments.asyncio import ensure_installed
from tests.compat import mock
from tests.tools import async_test


def create_task(coro):
    """Provide interface to create_task regardless of python version."""
    if hasattr(asyncio, "create_task"):  # py37+
        return asyncio.create_task(coro)
    return asyncio.get_event_loop().create_task(coro)


async def coro(value=None, wait=None, loop=None):
    """Helper function for testing coroutines.

    :value: This will be inserted into the ``tags`` of ``instrument``.
    :wait: A float of seconds to be waited before calling ``instrument``.
    :loop: EventLoop to be used if any.
    :returns: nothing.
    """

    if wait:
        await asyncio.sleep(wait, loop=loop)
    tags = {"value": value} if value else None
    with instrument("coro", tags=tags):
        await asyncio.sleep(0.1, loop=loop)


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


def test_ensure_installed_twice(caplog):
    ensure_installed()
    ensure_installed()

    assert caplog.record_tuples == 2 * [
        (
            "scout_apm.instruments.asyncio",
            logging.DEBUG,
            "Instrumenting asyncio.",
        )
    ]


def test_install_fail_no_asyncio(caplog):
    mock_no_asyncio = mock.patch("scout_apm.instruments.asyncio.asyncio", new=None)
    with mock_no_asyncio:
        ensure_installed()

    assert caplog.record_tuples == [
        (
            "scout_apm.instruments.asyncio",
            logging.DEBUG,
            "Instrumenting asyncio.",
        ),
        (
            "scout_apm.instruments.asyncio",
            logging.DEBUG,
            "Couldn't import asyncio - probably old version of python.",
        ),
    ]


@async_test
async def test_coroutine(tracked_request):
    ensure_installed()
    with BackgroundTransaction("test"):
        await coro()

    assert len(tracked_request.complete_spans) == 2
    span = tracked_request.complete_spans[0]
    assert span.operation == "Custom/coro"
    assert tracked_request.complete_spans[1].operation == "Job/test"


@async_test
async def test_coroutine_timeout(tracked_request):
    ensure_installed()
    with BackgroundTransaction("test"):
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(coro("long", wait=0.5), timeout=0.1)

    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Job/test"


@async_test
async def test_task_awaited(tracked_request):
    ensure_installed()
    with BackgroundTransaction("test"):
        await create_task(coro())

    assert len(tracked_request.complete_spans) == 2
    span = tracked_request.complete_spans[0]
    assert span.operation == "Custom/coro"
    assert tracked_request.complete_spans[1].operation == "Job/test"


@async_test
async def test_nested_tasks(tracked_request):
    async def orchestrator():
        await coro("1")
        await asyncio.gather(
            # Force this coroutine to finish later for idempotency
            coro("2a", wait=0.5),
            coro("2b"),
        )

    ensure_installed()
    with BackgroundTransaction("test"):
        await orchestrator()

    spans = tracked_request.complete_spans
    assert len(spans) == 4
    assert [span.operation for span in spans] == [
        "Custom/coro",
        "Custom/coro",
        "Custom/coro",
        "Job/test",
    ]
    # Verify the order of the coroutines
    assert [span.tags.get("value") for span in spans] == [
        "1",
        "2b",
        "2a",
        None,
    ]


@async_test
async def test_task_not_awaited(tracked_request):
    ensure_installed()
    with BackgroundTransaction("test"):
        await create_task(coro("short"))
        long = create_task(coro("long", wait=0.5))

    assert len(tracked_request.complete_spans) == 2
    span = tracked_request.complete_spans[0]
    assert span.operation == "Custom/coro"
    assert span.tags["value"] == "short"
    assert tracked_request.complete_spans[1].operation == "Job/test"

    assert not long.done()
    await long
    assert len(tracked_request.complete_spans) == 3
    span = tracked_request.complete_spans[2]
    assert span.operation == "Custom/coro"
    assert span.tags["value"] == "long"


@async_test
async def test_task_cancelled(tracked_request):
    ensure_installed()
    with BackgroundTransaction("test"):
        long = create_task(coro("long", wait=0.5))
        long.cancel()

    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Job/test"


@async_test
async def test_future_awaited(tracked_request):
    ensure_installed()
    with BackgroundTransaction("test"):
        fut = get_future()
        create_task(set_future(fut, wait=0.5))
        await fut
        assert len(tracked_request.complete_spans) == 1
        assert tracked_request.complete_spans[0].operation == "Custom/set_future"

    assert len(tracked_request.complete_spans) == 2
    assert tracked_request.complete_spans[1].operation == "Job/test"


@async_test
async def test_future_gathered(tracked_request):
    ensure_installed()
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


@async_test
async def test_future_not_gathered(tracked_request):
    ensure_installed()
    with BackgroundTransaction("test"):
        gather_future = asyncio.gather(
            resolving_future(0.5),
            coro(wait=0.5),
        )

    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Job/test"

    await gather_future
    assert len(tracked_request.complete_spans) == 3
    # gather can run the coroutines/futures in any order.
    operations = {span.operation for span in tracked_request.complete_spans[1:]}
    assert operations == {"Custom/set_future", "Custom/coro"}


@async_test
async def test_future_cancelled(tracked_request):
    ensure_installed()
    with BackgroundTransaction("test"):
        gather_future = asyncio.gather(
            resolving_future(0.5),
            coro(wait=0.5),
        )
        gather_future.cancel()

    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Job/test"
