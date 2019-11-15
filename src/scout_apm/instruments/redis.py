# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

import wrapt

from scout_apm.core.tracked_request import TrackedRequest

try:
    import redis
except ImportError:  # pragma: no cover
    redis = None
else:
    if redis.VERSION[0] >= 3:
        from redis import Redis
        from redis.client import Pipeline
    else:  # pragma: no cover
        from redis import StrictRedis as Redis
        from redis.client import BasePipeline as Pipeline

logger = logging.getLogger(__name__)


have_patched_redis_execute_command = False
have_patched_pipeline_execute = False


def ensure_installed():
    global have_patched_redis_execute_command, have_patched_pipeline_execute

    logger.info("Ensuring redis instrumentation is installed.")

    if redis is None:
        logger.info("Unable to import redis")
    else:
        if not have_patched_redis_execute_command:
            try:
                Redis.execute_command = wrapped_execute_command(Redis.execute_command)
            except Exception as exc:
                logger.warning(
                    "Unable to instrument redis.Redis.execute_command: %r",
                    exc,
                    exc_info=exc,
                )
            else:
                have_patched_redis_execute_command = True

        if not have_patched_pipeline_execute:
            try:
                Pipeline.execute = wrapped_execute(Pipeline.execute)
            except Exception as exc:
                logger.warning(
                    "Unable to instrument redis.Pipeline.execute: %r", exc, exc_info=exc
                )
            else:
                have_patched_pipeline_execute = True

    return True


@wrapt.decorator
def wrapped_execute_command(wrapped, instance, args, kwargs):
    try:
        op = args[0]
    except (IndexError, TypeError):
        op = "Unknown"

    tracked_request = TrackedRequest.instance()
    tracked_request.start_span(operation="Redis/{}".format(op))

    try:
        return wrapped(*args, **kwargs)
    finally:
        tracked_request.stop_span()


@wrapt.decorator
def wrapped_execute(wrapped, instance, args, kwargs):
    tracked_request = TrackedRequest.instance()
    tracked_request.start_span(operation="Redis/MULTI")

    try:
        return wrapped(*args, **kwargs)
    finally:
        tracked_request.stop_span()
