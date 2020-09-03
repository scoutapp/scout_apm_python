# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

try:
    from aioredis import Redis
except ImportError:  # pragma: no cover
    Redis = None

try:
    from aioredis.commands import Pipeline
except ImportError:
    Pipeline = None

# The async_ module can only be shipped on Python 3.6+
try:
    from scout_apm.async_.instruments.aioredis import (
        wrapped_pipeline_execute,
        wrapped_redis_execute,
    )
except ImportError:
    wrapped_redis_execute = None
    wrapped_pipeline_execute = None

logger = logging.getLogger(__name__)

have_patched_redis_execute = False
have_patched_pipeline_execute = False


def ensure_installed():
    global have_patched_redis_execute, have_patched_pipeline_execute

    logger.debug("Instrumenting aioredis.")

    if Redis is None:
        logger.debug("Couldn't import aioredis.Redis - probably not installed.")
    elif wrapped_redis_execute is None:
        logger.debug(
            "Couldn't import scout_apm.async_.instruments.aioredis -"
            + " probably using Python < 3.6."
        )
    elif not have_patched_redis_execute:
        try:
            Redis.execute = wrapped_redis_execute(Redis.execute)
        except Exception as exc:
            logger.warning(
                "Failed to instrument aioredis.Redis.execute: %r",
                exc,
                exc_info=exc,
            )
        else:
            have_patched_redis_execute = True

    if Pipeline is None:
        logger.debug(
            "Couldn't import aioredis.commands.Pipeline - probably not installed."
        )
    elif wrapped_pipeline_execute is None:
        logger.debug(
            "Couldn't import scout_apm.async_.instruments.aioredis -"
            + " probably using Python < 3.6."
        )
    elif not have_patched_pipeline_execute:
        try:
            Pipeline.execute = wrapped_pipeline_execute(Pipeline.execute)
        except Exception as exc:
            logger.warning(
                "Failed to instrument aioredis.commands.Pipeline.execute: %r",
                exc,
                exc_info=exc,
            )
        else:
            have_patched_pipeline_execute = True
