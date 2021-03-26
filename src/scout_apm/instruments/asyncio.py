# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

import wrapt

from scout_apm.core.context import (
    SCOUT_REQUEST_ATTR,
    TrackedRequest,
    get_current_asyncio_task,
)

try:
    import asyncio
except ImportError:
    asyncio = None

logger = logging.getLogger(__name__)

have_patched_asyncio = False


def wrapped_create_task(wrapped, instance, args, kwargs):
    """Wrapper for ``create_task(coro)`` that propagates the current
    ``TrackedRequest`` to the new ``Task``.
    """
    new_task = wrapped(*args, **kwargs)
    current_task = get_current_asyncio_task()

    tracked_request = (
        getattr(current_task, SCOUT_REQUEST_ATTR, None) or TrackedRequest.instance()
    )

    if tracked_request.is_real_request and not tracked_request.is_ignored():
        # Updates the ``TrackedRequest`` for the given Task.
        # Used to pass the request amongst different tasks.
        setattr(new_task, SCOUT_REQUEST_ATTR, tracked_request)

    return new_task


def ensure_installed():
    global have_patched_asyncio

    logger.debug("Instrumenting asyncio.")

    if asyncio is None:
        logger.debug("Couldn't import asyncio - probably old version of python.")
    else:
        if not have_patched_asyncio:
            try:
                wrapt.wrap_function_wrapper(
                    asyncio.BaseEventLoop, "create_task", wrapped_create_task
                )
            except Exception as exc:
                logger.warning(
                    "Failed to instrument asyncio.create_task: %r",
                    exc,
                    exc_info=exc,
                )
            else:
                have_patched_asyncio = True

    return True
