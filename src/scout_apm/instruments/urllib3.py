# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

import wrapt

from scout_apm.compat import text_type
from scout_apm.core.tracked_request import TrackedRequest

try:
    from urllib3 import HTTPConnectionPool
except ImportError:
    HTTPConnectionPool = None

logger = logging.getLogger(__name__)


class Instrument(object):
    installed = False

    def installable(self):
        if HTTPConnectionPool is None:
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
            HTTPConnectionPool.urlopen = wrapped_urlopen(HTTPConnectionPool.urlopen)
        except Exception as exc:
            logger.warning(
                "Unable to instrument for Urllib3 HTTPConnectionPool.urlopen: %r",
                exc,
                exc_info=exc,
            )
            return False

        logger.info("Instrumented Urllib3")
        return True

    def uninstall(self):
        if not self.installed:
            logger.info("Urllib3 instruments are not installed. Skipping.")
            return False

        self.__class__.installed = False

        HTTPConnectionPool.urlopen = HTTPConnectionPool.urlopen.__wrapped__


@wrapt.decorator
def wrapped_urlopen(wrapped, instance, args, kwargs):
    def _extract_method(method, *args, **kwargs):
        return method

    try:
        method = _extract_method(*args, **kwargs)
    except TypeError:
        method = "Unknown"

    try:
        url = text_type(instance._absolute_url("/"))
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
