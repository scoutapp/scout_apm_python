# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

import wrapt

from scout_apm.core.tracked_request import TrackedRequest

try:
    from jinja2 import Template
except ImportError:  # pragma: no cover
    Template = None

logger = logging.getLogger(__name__)


attempted = False


def install():
    global attempted

    if attempted:
        logger.warning(
            "Jinja2 instrumentation has already been attempted to be installed."
        )
        return False

    attempted = True

    if Template is None:
        logger.info("Unable to import Jinja2's Template")
        return False

    try:
        Template.render = wrapped_render(Template.render)
    except Exception as exc:
        logger.warning(
            "Unable to instrument for Jinja2 Template.render: %r", exc, exc_info=exc
        )
        return False
    logger.info("Instrumented Jinja2")
    return True


@wrapt.decorator
def wrapped_render(wrapped, instance, args, kwargs):
    tracked_request = TrackedRequest.instance()
    span = tracked_request.start_span(operation="Template/Render")
    span.tag("name", instance.name)
    try:
        return wrapped(*args, **kwargs)
    finally:
        tracked_request.stop_span()
