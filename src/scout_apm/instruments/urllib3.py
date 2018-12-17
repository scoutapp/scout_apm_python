from __future__ import absolute_import, division, print_function, unicode_literals

import logging

from scout_apm.core.monkey import monkeypatch_method, unpatch_method
from scout_apm.core.tracked_request import TrackedRequest

logger = logging.getLogger(__name__)


class Instrument(object):
    def __init__(self):
        self.installed = False

    def installable(self):
        try:
            from urllib3 import HTTPConnectionPool, PoolManager  # noqa: F401
        except ImportError:
            logger.info("Unable to import for Urllib3 instruments")
            return False
        if self.installed:
            logger.warn("Urllib3 Instruments are already installed.")
            return False
        return True

    def install(self):
        if not self.installable():
            logger.info("Urllib3 instruments are not installable. Skipping.")
            return False

        self.installed = True

        try:
            from urllib3 import HTTPConnectionPool

            @monkeypatch_method(HTTPConnectionPool)
            def urlopen(original, self, *args, **kwargs):
                method = "Unknown"
                url = "Unknown"
                try:
                    try:
                        method = kwargs["method"]
                    except KeyError:
                        method = args[0]
                    url = "{}".format(self._absolute_url("/"))
                except Exception as e:
                    logger.error(
                        "Could not get instrument data for HTTPConnectionPool: %r", e
                    )

                tr = TrackedRequest.instance()
                span = tr.start_span(operation="HTTP/{}".format(method))
                span.tag("url", "{}".format(url))

                try:
                    return original(*args, **kwargs)
                finally:
                    tr.stop_span()

            logger.info("Instrumented Urllib3")

        except Exception as e:
            logger.warn(
                "Unable to instrument for Urllib3 HTTPConnectionPool.urlopen: %r", e
            )
            return False
        return True

    def uninstall(self):
        if not self.installed:
            logger.info("Urllib3 instruments are not installed. Skipping.")
            return False

        self.installed = False

        from urllib3 import HTTPConnectionPool

        unpatch_method(HTTPConnectionPool, "urlopen")
