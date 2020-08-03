# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

import wrapt

from scout_apm.core.tracked_request import TrackedRequest

try:
    import aioredis
except ImportError:
    aioredis = None
else:
    from aioredis import Redis as AioRedis
    from aioredis.commands import Pipeline as AioPipeline

logger = logging.getLogger(__name__)


have_patched_aioredis_execute = False
have_patched_aiopipeline_execute = False


def ensure_async_installed():
    global have_patched_aioredis_execute, have_patched_aiopipeline_execute

    if aioredis is None:
        logger.debug("Couldn't import aioredis - probably not installed")
        return

    if wrapped_execute_async is None or wrapped_execute_command_async is None:
        logger.debug("Couldn't import async wrapper - probably async not supported")
        return

    if not have_patched_aioredis_execute:
        try:
            AioRedis.execute = wrapped_execute_command_async(AioRedis.execute)
        except Exception as exc:
            logger.warning(
                "Failed to instrument aioredis.Redis.execute: %r", exc, exc_info=exc
            )
        else:
            have_patched_aioredis_execute = True

    if not have_patched_aiopipeline_execute:
        try:
            AioPipeline.execute = wrapped_execute_command_async(AioPipeline.execute)
        except Exception as exc:
            logger.warning(
                "Failed to instrument aioredis.Redis.execute: %r", exc, exc_info=exc
            )
        else:
            have_patched_aiopipeline_execute = True


@wrapt.decorator
async def wrapped_execute_command_async(wrapped, instance, args, kwargs):
    try:
        op = args[0]
        if isinstance(op, bytes):
            op = op.decode()
    except (IndexError, TypeError):
        op = "Unknown"

    tracked_request = TrackedRequest.instance()
    tracked_request.start_span(operation="Redis/{}".format(op))

    try:
        return await wrapped(*args, **kwargs)
    finally:
        tracked_request.stop_span()


@wrapt.decorator
async def wrapped_execute_async(wrapped, instance, args, kwargs):
    tracked_request = TrackedRequest.instance()
    tracked_request.start_span(operation="Redis/MULTI")

    try:
        return await wrapped(*args, **kwargs)
    finally:
        tracked_request.stop_span()
