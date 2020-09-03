# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import wrapt

from scout_apm.core.tracked_request import TrackedRequest


@wrapt.decorator
async def wrapped_render_async(wrapped, instance, args, kwargs):
    tracked_request = TrackedRequest.instance()
    with tracked_request.span(operation="Template/Render") as span:
        span.tag("name", instance.name)
        return await wrapped(*args, **kwargs)
