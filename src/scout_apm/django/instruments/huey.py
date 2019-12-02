# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

from django.conf import settings

logger = logging.getLogger(__name__)

instrumented = False


def ensure_instrumented():
    global instrumented
    if instrumented:
        return
    instrumented = True

    # Avoid importing if not installed
    if "huey.contrib.djhuey" not in settings.INSTALLED_APPS:  # pragma: no cover
        return

    try:
        from huey.contrib.djhuey import HUEY
    except ImportError:  # pragma: no cover
        return

    from scout_apm.huey import attach_scout_handlers

    attach_scout_handlers(HUEY)
    logger.debug("Instrumented huey.contrib.djhuey")
