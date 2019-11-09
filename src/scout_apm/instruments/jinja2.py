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


have_patched_template_render = False


def ensure_installed():
    global have_patched_template_render

    logger.info("Ensuring Jinja2 instrumentation is installed.")

    if Template is None:
        logger.info("Unable to import jinja2.Template")
    elif not have_patched_template_render:
        try:
            Template.render = wrapped_render(Template.render)
        except Exception as exc:
            logger.warning(
                "Unable to instrument jinja2.Template.render: %r", exc, exc_info=exc
            )
        else:
            have_patched_template_render = True


@wrapt.decorator
def wrapped_render(wrapped, instance, args, kwargs):
    tracked_request = TrackedRequest.instance()
    span = tracked_request.start_span(operation="Template/Render")
    span.tag("name", instance.name)
    try:
        return wrapped(*args, **kwargs)
    finally:
        tracked_request.stop_span()
