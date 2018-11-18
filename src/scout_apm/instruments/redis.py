from __future__ import absolute_import, division, print_function, unicode_literals

import logging

from scout_apm.core.monkey import monkeypatch_method
from scout_apm.core.tracked_request import TrackedRequest

logger = logging.getLogger(__name__)


class Instrument(object):
    def __init__(self):
        self.installed = False

    def installable(self):
        try:
            from redis import StrictRedis  # noqa: F401
            from redis.client import BasePipeline  # noqa: F401
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

        self.patch_strictredis()
        self.patch_basepipeline()

        logger.info("Instrumented Redis")
        return True

    def patch_strictredis(self):
        try:
            from redis import StrictRedis

            @monkeypatch_method(StrictRedis)
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

    def patch_basepipeline(self):
        try:
            from redis.client import BasePipeline

            @monkeypatch_method(BasePipeline)
            def execute(original, self, *args, **kwargs):
                tr = TrackedRequest.instance()
                tr.start_span(operation="Redis/MULTI")

                try:
                    return original(*args, **kwargs)
                finally:
                    tr.stop_span()

        except Exception as e:
            logger.warn("Unable to instrument for Redis BasePipeline.execute: %r", e)
