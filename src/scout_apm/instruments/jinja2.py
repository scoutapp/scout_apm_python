from __future__ import absolute_import, division, print_function, unicode_literals

import logging

from scout_apm.core.monkey import monkeypatch_method, unpatch_method
from scout_apm.core.tracked_request import TrackedRequest

logger = logging.getLogger(__name__)


class Instrument(object):
    def __init__(self):
        self.installed = False

    def installable(self):
        try:
            from jinja2 import Template  # noqa: F401
        except ImportError:
            logger.info("Unable to import for Jinja2 instruments")
            return False
        if self.installed:
            logger.warn("Jinja2 Instruments are already installed.")
            return False
        return True

    def install(self):
        if not self.installable():
            logger.info("Jinja2 instruments are not installable. Skipping.")
            return False

        self.installed = True

        try:
            from jinja2 import Template

            @monkeypatch_method(Template)
            def render(original, self, *args, **kwargs):
                tr = TrackedRequest.instance()
                span = tr.start_span(operation="Template/Render")
                span.tag("name", self.name)

                try:
                    return original(*args, **kwargs)
                finally:
                    tr.stop_span()

            logger.info("Instrumented Jinja2")

        except Exception as e:
            logger.warn("Unable to instrument for Jinja2 Template.render: %r", e)
            return False
        return True

    def uninstall(self):
        if not self.installed:
            logger.info("Jinja2 instruments are not installed. Skipping.")
            return False

        self.installed = False

        from jinja2 import Template

        unpatch_method(Template, "render")
