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

installed = False


def install():
    global installed

    if installed:
        logger.warning("Urllib3 Instruments are already installed.")
        return True

    if HTTPConnectionPool is None:
        logger.info("Unable to import urllib3.HTTPConnectionPool")
        return False

    try:
        HTTPConnectionPool.urlopen = wrapped_urlopen(HTTPConnectionPool.urlopen)
    except Exception as exc:
        logger.warning(
            "Unable to instrument for Urllib3 HTTPConnectionPool.urlopen: %r",
            exc,
            exc_info=exc,
        )
        return False

    installed = True
    return True


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
