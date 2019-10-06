# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

from scout_apm.core.monkey import monkeypatch_method, unpatch_method
from scout_apm.core.tracked_request import TrackedRequest

logger = logging.getLogger(__name__)


class Instrument(object):
    installed = False

    def installable(self):
        try:
            from jinja2 import Template  # noqa: F401
        except ImportError:
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
            from jinja2 import Template

            @monkeypatch_method(Template)
            def render(original, self, *args, **kwargs):
                tracked_request = TrackedRequest.instance()
                span = tracked_request.start_span(operation="Template/Render")
                span.tag("name", self.name)

                try:
                    return original(*args, **kwargs)
                finally:
                    tracked_request.stop_span()

            logger.info("Instrumented Jinja2")

        except Exception as e:
            logger.warning("Unable to instrument for Jinja2 Template.render: %r", e)
            return False
        return True

    def uninstall(self):
        if not self.installed:
            logger.info("Jinja2 instruments are not installed. Skipping.")
            return False

        self.__class__.installed = False

        from jinja2 import Template

        unpatch_method(Template, "render")
