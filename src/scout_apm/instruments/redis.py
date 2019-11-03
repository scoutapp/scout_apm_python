# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

import wrapt

from scout_apm.core.tracked_request import TrackedRequest

logger = logging.getLogger(__name__)


def import_Redis_and_Pipeline():
    import redis  # noqa: F401

    if redis.VERSION[0] >= 3:
        from redis import Redis  # noqa: F401
        from redis.client import Pipeline  # noqa: F401
    else:  # pragma: no cover
        from redis import StrictRedis as Redis  # noqa: F401
        from redis.client import BasePipeline as Pipeline  # noqa: F401

    return Redis, Pipeline


class Instrument(object):
    installed = False

    def installable(self):
        try:
            Redis, Pipeline = import_Redis_and_Pipeline()
        except ImportError:
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
        try:
            Redis, _Pipeline = import_Redis_and_Pipeline()

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

            Redis.execute_command = wrapped_execute_command(Redis.execute_command)

        except Exception as e:
            logger.warning(
                "Unable to instrument for Redis StrictRedis.execute_command: %r", e
            )

    def unpatch_redis(self):
        Redis, _Pipeline = import_Redis_and_Pipeline()

        Redis.execute_command = Redis.execute_command.__wrapped__

    def patch_pipeline(self):
        try:
            _Redis, Pipeline = import_Redis_and_Pipeline()

            @wrapt.decorator
            def wrapped_execute(wrapped, instance, args, kwargs):
                tracked_request = TrackedRequest.instance()
                tracked_request.start_span(operation="Redis/MULTI")

                try:
                    return wrapped(*args, **kwargs)
                finally:
                    tracked_request.stop_span()

            Pipeline.execute = wrapped_execute(Pipeline.execute)

        except Exception as e:
            logger.warning("Unable to instrument for Redis BasePipeline.execute: %r", e)

    def unpatch_pipeline(self):
        _Redis, Pipeline = import_Redis_and_Pipeline()

        Pipeline.execute = Pipeline.execute.__wrapped__
