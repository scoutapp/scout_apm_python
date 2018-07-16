from __future__ import absolute_import

import logging

from scout_apm.core.tracked_request import TrackedRequest
from scout_apm.core.monkey import monkeypatch_method

logger = logging.getLogger(__name__)


class Instrument:
    def __init__(self):
        self.installed = False

    def installable(self):
        try:
            from urllib3 import HTTPConnectionPool, PoolManager
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

        self.patch_connectionpool()

        logger.info("Instrumented Urllib3")
        return True

    def patch_connectionpool(self):
        try:
            from urllib3 import HTTPConnectionPool

            @monkeypatch_method(HTTPConnectionPool)
            def urlopen(original, self, *args, **kwargs):
                method = 'Unknown'
                url = 'Unknown'
                try:
                    if 'method' in kwargs:
                        method = kwargs['method']
                    else:
                        method = args[0]
                    url = '{}'.format(self._absolute_url('/'))
                except Exception as e:
                    logger.error('Could not get instrument data for HTTPConnectionPool: {}'.format(repr(e)))

                tr = TrackedRequest.instance()
                span = tr.start_span(operation='HTTP/{}'.format(method))
                span.tag('url', '{}'.format(url))

                try:
                    return original(*args, **kwargs)
                finally:
                    tr.stop_span()
        except Exception as e:
            logger.warn('Unable to instrument for Urllib3 HTTPConnectionPool.urlopen: {}'.format(repr(e)))
