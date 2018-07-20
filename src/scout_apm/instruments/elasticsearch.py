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
            from elasticsearch import Transport
        except ImportError:
            logger.info("Unable to import for ElasticSearch instruments")
            return False
        if self.installed:
            logger.warn("ElasticSearch Instruments are already installed.")
            return False
        return True

    def install(self):
        if not self.installable():
            logger.info("ElasticSearch instruments are not installable. Skipping.")
            return False

        self.installed = True

        try:
            from elasticsearch import Transport

            def _sanitize_name(name):
                try:
                    op = name.split("/")[-1]
                    op = op[1:]  # chop leading '_' from op
                    allowed_names = ["bench",
                                     "bulk",
                                     "count",
                                     "exists",
                                     "explain",
                                     "field_stats",
                                     "health",
                                     "mget",
                                     "mlt",
                                     "mpercolate",
                                     "msearch",
                                     "mtermvectors",
                                     "percolate",
                                     "query",
                                     "scroll",
                                     "search_shards",
                                     "source",
                                     "suggest",
                                     "template",
                                     "termvectors",
                                     "update",
                                     "search"]

                    if op in allowed_names:
                        return op.title()
                    return 'Unknown'
                except Exception:
                    return 'Unknown'

            @monkeypatch_method(Transport)
            def perform_request(original, self, *args, **kwargs):
                try:
                    op = _sanitize_name(args[1])
                except IndexError:
                    op = 'Unknown'

                tr = TrackedRequest.instance()
                span = tr.start_span(operation='Elasticsearch/{}'.format(op), ignore_children=True)

                try:
                    return original(*args, **kwargs)
                finally:
                    tr.stop_span()

            logger.info("Instrumented ElasticSearch")

        except Exception as e:
            logger.warn('Unable to instrument for ElasticSearch Transport.perform_request: {}'.format(repr(e)))
        return True
