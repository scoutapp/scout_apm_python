from __future__ import absolute_import, division, print_function, unicode_literals

import logging

from scout_apm.core.monkey import monkeypatch_method, unpatch_method
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
    def __init__(self):
        self.installed = False

    def installable(self):
        try:
            Redis, Pipeline = import_Redis_and_Pipeline()
        except ImportError:
            logger.info("Unable to import for Redis instruments")
            return False
        if self.installed:
            logger.warn("Redis Instruments are already installed.")
            return False
        return True

    def install(self):
        if not self.installable():
            logger.info("Redis instruments are not installable. Skipping.")
            return False

        self.installed = True

        self.patch_redis()
        self.patch_pipeline()

        logger.info("Instrumented Redis")
        return True

    def uninstall(self):
        if not self.installed:
            logger.info("Redis instruments are not installed. Skipping.")
            return False

        self.installed = False

        self.unpatch_redis()
        self.unpatch_pipeline()

    def patch_redis(self):
        try:
            Redis, _Pipeline = import_Redis_and_Pipeline()

            @monkeypatch_method(Redis)
            def execute_command(original, self, *args, **kwargs):
                try:
                    op = args[0]
                except (IndexError, TypeError):
                    op = "Unknown"

                tr = TrackedRequest.instance()
                tr.start_span(operation="Redis/{}".format(op))

                try:
                    return original(*args, **kwargs)
                finally:
                    tr.stop_span()

        except Exception as e:
            logger.warn(
                "Unable to instrument for Redis StrictRedis.execute_command: %r", e
            )

    def unpatch_redis(self):
        Redis, _Pipeline = import_Redis_and_Pipeline()

        unpatch_method(Redis, "execute_command")

    def patch_pipeline(self):
        try:
            _Redis, Pipeline = import_Redis_and_Pipeline()

            @monkeypatch_method(Pipeline)
            def execute(original, self, *args, **kwargs):
                tr = TrackedRequest.instance()
                tr.start_span(operation="Redis/MULTI")

                try:
                    return original(*args, **kwargs)
                finally:
                    tr.stop_span()

        except Exception as e:
            logger.warn("Unable to instrument for Redis BasePipeline.execute: %r", e)

    def unpatch_pipeline(self):
        _Redis, Pipeline = import_Redis_and_Pipeline()

        unpatch_method(Pipeline, "execute")
