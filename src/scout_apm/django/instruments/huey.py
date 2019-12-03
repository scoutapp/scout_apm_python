# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

from django.apps import apps

logger = logging.getLogger(__name__)

huey_instrumented = False


def ensure_huey_instrumented():
    global huey_instrumented
    if huey_instrumented:
        return
    huey_instrumented = True

    # Avoid importing if not installed
    if not apps.is_installed("huey.contrib.djhuey"):  # pragma: no cover
        return

    try:
        from huey.contrib.djhuey import HUEY
    except ImportError:  # pragma: no cover
        return

    from scout_apm.huey import attach_scout_handlers

    attach_scout_handlers(HUEY)
    logger.debug("Instrumented huey.contrib.djhuey")
