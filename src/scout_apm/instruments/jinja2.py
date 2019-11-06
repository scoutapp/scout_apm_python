# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

import wrapt

from scout_apm.core.tracked_request import TrackedRequest

try:
    from jinja2 import Template
except ImportError:
    Template = None

logger = logging.getLogger(__name__)


class Instrument(object):
    installed = False

    def installable(self):
        if Template is None:
            logger.info("Unable to import for Jinja2 instruments")
            return False
        if self.installed:
            logger.warning("Jinja2 Instruments are already installed.")
            return False
        return True

    def install(self):
        if not self.installable():
            logger.info("Jinja2 instruments are not installable. Skipping.")
            return False

        self.__class__.installed = True

        try:
            Template.render = wrapped_render(Template.render)
        except Exception as exc:
            logger.warning(
                "Unable to instrument for Jinja2 Template.render: %r", exc, exc_info=exc
            )
            return False
        logger.info("Instrumented Jinja2")
        return True

    def uninstall(self):
        if not self.installed:
            logger.info("Jinja2 instruments are not installed. Skipping.")
            return False

        self.__class__.installed = False

        Template.render = Template.render.__wrapped__


@wrapt.decorator
def wrapped_render(wrapped, instance, args, kwargs):
    tracked_request = TrackedRequest.instance()
    span = tracked_request.start_span(operation="Template/Render")
    span.tag("name", instance.name)
    try:
        return wrapped(*args, **kwargs)
    finally:
        tracked_request.stop_span()
