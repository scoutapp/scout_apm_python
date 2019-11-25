# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

import wrapt

from scout_apm.core.tracked_request import TrackedRequest

try:
    from jinja2 import Template
except ImportError:  # pragma: no cover
    Template = None

# The async_ module can only be shipped on Python 3.6+
try:
    from scout_apm.async_.instruments.jinja2 import wrapped_render_async
except ImportError:
    wrapped_render_async = None


logger = logging.getLogger(__name__)


have_patched_template_render = False
have_patched_template_render_async = False


def ensure_installed():
    global have_patched_template_render
    global have_patched_template_render_async

    logger.info("Ensuring Jinja2 instrumentation is installed.")

    if Template is None:
        logger.info("Unable to import jinja2.Template")
        return

    if not have_patched_template_render:
        try:
            Template.render = wrapped_render(Template.render)
        except Exception as exc:
            logger.warning(
                "Unable to instrument jinja2.Template.render: %r", exc, exc_info=exc
            )
        else:
            have_patched_template_render = True

    if not have_patched_template_render_async and wrapped_render_async is not None:
        try:
            Template.render_async = wrapped_render_async(Template.render_async)
        except Exception as exc:
            logger.warning(
                "Unable to instrument jinja2.Template.render_async: %r",
                exc,
                exc_info=exc,
            )
        else:
            have_patched_template_render_async = True


@wrapt.decorator
def wrapped_render(wrapped, instance, args, kwargs):
    tracked_request = TrackedRequest.instance()
    span = tracked_request.start_span(operation="Template/Render")
    span.tag("name", instance.name)
    try:
        return wrapped(*args, **kwargs)
    finally:
        tracked_request.stop_span()
