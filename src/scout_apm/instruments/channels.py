# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

try:
    from channels.generic.http import AsyncHttpConsumer
except ImportError:  # pragma: no cover
    AsyncHttpConsumer = None

# The async_ module can only be shipped on Python 3.6+
try:
    from scout_apm.async_.instruments.channels import wrapped_http_request
except ImportError:
    wrapped_http_request = None


logger = logging.getLogger(__name__)

have_patched_http_consumer = False


def ensure_installed():
    global have_patched_http_consumer

    logger.info("Ensuring Channels instrumentation is installed.")

    if AsyncHttpConsumer is None:
        logger.info("Unable to import channels.generic.http.AsyncHttpConsumer")
        return

    if not have_patched_http_consumer and wrapped_http_request is not None:
        try:
            AsyncHttpConsumer.http_request = wrapped_http_request(AsyncHttpConsumer.http_request)
        except Exception as exc:
            logger.warning(
                "Unable to instrument channels.generic.http.AsyncHttpConsumer.http_request: %r",
                exc,
                exc_info=exc,
            )
        else:
            have_patched_http_consumer = True
