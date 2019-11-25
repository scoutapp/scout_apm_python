# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

logger = logging.getLogger(__name__)

huey_instrumented = False


def ensure_huey_instrumented():
    global huey_instrumented
    if huey_instrumented:
        return
    huey_instrumented = True

    try:
        from huey.contrib.djhuey import HUEY
    except ImportError:
        return

    from scout_apm.huey import attach_scout_handlers

    attach_scout_handlers(HUEY)
    logger.debug("Instrumented huey.contrib.djhuey")
