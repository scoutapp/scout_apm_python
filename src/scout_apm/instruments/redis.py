# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

import wrapt

from scout_apm.core.tracked_request import TrackedRequest

try:
    import redis
except ImportError:
    redis = None
else:
    if redis.VERSION[0] >= 3:
        from redis import Redis
        from redis.client import Pipeline
    else:  # pragma: no cover
        from redis import StrictRedis as Redis
        from redis.client import BasePipeline as Pipeline

logger = logging.getLogger(__name__)


class Instrument(object):
    installed = False

    def installable(self):
        if redis is None:
            logger.info("Unable to import for Redis instruments")
            return False
        if self.installed:
            logger.warning("Redis Instruments are already installed.")
            return False
        return True

    def install(self):
        if not self.installable():
            logger.info("Redis instruments are not installable. Skipping.")
            return False

        self.__class__.installed = True

        self.patch_redis()
        self.patch_pipeline()

        logger.info("Instrumented Redis")
        return True

    def uninstall(self):
        if not self.installed:
            logger.info("Redis instruments are not installed. Skipping.")
            return False

        self.__class__.installed = False

        self.unpatch_redis()
        self.unpatch_pipeline()

    def patch_redis(self):
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

        try:
            Redis.execute_command = wrapped_execute_command(Redis.execute_command)
        except Exception as exc:
            logger.warning(
                "Unable to instrument for Redis Redis.execute_command: %r",
                exc,
                exc_info=exc,
            )

    def unpatch_redis(self):
        Redis.execute_command = Redis.execute_command.__wrapped__

    def patch_pipeline(self):
        @wrapt.decorator
        def wrapped_execute(wrapped, instance, args, kwargs):
            tracked_request = TrackedRequest.instance()
            tracked_request.start_span(operation="Redis/MULTI")

            try:
                return wrapped(*args, **kwargs)
            finally:
                tracked_request.stop_span()

        try:
            Pipeline.execute = wrapped_execute(Pipeline.execute)
        except Exception as exc:
            logger.warning(
                "Unable to instrument for Redis BasePipeline.execute: %r",
                exc,
                exc_info=exc,
            )

    def unpatch_pipeline(self):
        Pipeline.execute = Pipeline.execute.__wrapped__
