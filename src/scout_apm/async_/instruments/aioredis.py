# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import wrapt

from scout_apm.core.tracked_request import TrackedRequest


@wrapt.decorator
async def wrapped_redis_execute(wrapped, instance, args, kwargs):
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
async def wrapped_pipeline_execute(wrapped, instance, args, kwargs):
    tracked_request = TrackedRequest.instance()
    tracked_request.start_span(operation="Redis/MULTI")

    try:
        return await wrapped(*args, **kwargs)
    finally:
        tracked_request.stop_span()
