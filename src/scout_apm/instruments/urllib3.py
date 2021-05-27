# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

import wrapt

from scout_apm.compat import text_type
from scout_apm.core.config import scout_config
from scout_apm.core.tracked_request import TrackedRequest

try:
    from urllib3 import HTTPConnectionPool
except ImportError:  # pragma: no cover
    HTTPConnectionPool = None

logger = logging.getLogger(__name__)

have_patched_pool_urlopen = False


def ensure_installed():
    global have_patched_pool_urlopen

    logger.debug("Instrumenting urllib3.")

    if HTTPConnectionPool is None:
        logger.debug(
            "Couldn't import urllib3.HTTPConnectionPool - probably not installed."
        )
        return False
    elif not have_patched_pool_urlopen:
        try:
            HTTPConnectionPool.urlopen = wrapped_urlopen(HTTPConnectionPool.urlopen)
        except Exception as exc:
            logger.warning(
                "Failed to instrument for Urllib3 HTTPConnectionPool.urlopen: %r",
                exc,
                exc_info=exc,
            )
        else:
            have_patched_pool_urlopen = True


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

    # Don't instrument ErrorMonitor calls
    if text_type(url).startswith(scout_config.value("errors_host")):
        return wrapped(*args, **kwargs)

    tracked_request = TrackedRequest.instance()
    with tracked_request.span(operation="HTTP/{}".format(method)) as span:
        span.tag("url", text_type(url))
        return wrapped(*args, **kwargs)
