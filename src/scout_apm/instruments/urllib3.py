# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

import wrapt

from scout_apm.compat import text_type
from scout_apm.core.tracked_request import TrackedRequest

logger = logging.getLogger(__name__)


class Instrument(object):
    installed = False

    def installable(self):
        try:
            from urllib3 import HTTPConnectionPool, PoolManager  # noqa: F401
        except ImportError:
            logger.info("Unable to import for Urllib3 instruments")
            return False
        if self.installed:
            logger.warning("Urllib3 Instruments are already installed.")
            return False
        return True

    def install(self):
        if not self.installable():
            logger.info("Urllib3 instruments are not installable. Skipping.")
            return False

        self.__class__.installed = True

        try:
            from urllib3 import HTTPConnectionPool

            @wrapt.decorator
            def wrapped_urlopen(wrapped, instance, args, kwargs):
                def _extract_method(method, *args, **kwargs):
                    return method

                try:
                    method = _extract_method(*args, **kwargs)
                except TypeError:
                    method = "Unknown"

                try:
                    url = text_type(self._absolute_url("/"))
                except Exception:
                    logger.exception("Could not get URL for HTTPConnectionPool")
                    url = "Unknown"

                tracked_request = TrackedRequest.instance()
                span = tracked_request.start_span(operation="HTTP/{}".format(method))
                span.tag("url", text_type(url))

                try:
                    return wrapped(*args, **kwargs)
                finally:
                    tracked_request.stop_span()

            HTTPConnectionPool.urlopen = wrapped_urlopen(HTTPConnectionPool.urlopen)

            logger.info("Instrumented Urllib3")

        except Exception as e:
            logger.warning(
                "Unable to instrument for Urllib3 HTTPConnectionPool.urlopen: %r", e
            )
            return False
        return True

    def uninstall(self):
        if not self.installed:
            logger.info("Urllib3 instruments are not installed. Skipping.")
            return False

        self.__class__.installed = False

        from urllib3 import HTTPConnectionPool

        HTTPConnectionPool.urlopen = HTTPConnectionPool.urlopen.__wrapped__
