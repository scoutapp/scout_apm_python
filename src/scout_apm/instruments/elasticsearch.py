# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

import wrapt

from scout_apm.core.tracked_request import TrackedRequest

try:
    from elasticsearch import Elasticsearch, Transport
except ImportError:
    Elasticsearch = None
    Transport = None

logger = logging.getLogger(__name__)


class Instrument(object):
    installed = False

    CLIENT_METHODS = [
        "bulk",
        "count",
        "create",
        "delete",
        "delete_by_query",
        "exists",
        "exists_source",
        "explain",
        "field_caps",
        "get",
        "get_source",
        "index",
        "mget",
        "msearch",
        "msearch_template",
        "mtermvectors",
        "reindex",
        "reindex_rethrottle",
        "search",
        "search_shards",
        "search_template",
        "termvectors",
        "update",
        "update_by_query",
    ]

    def installable(self):
        if Elasticsearch is None:
            logger.info("Unable to import for Elasticsearch instruments")
            return False
        if self.installed:
            logger.warning("Elasticsearch Instruments are already installed.")
            return False
        return True

    def install(self):
        if not self.installable():
            logger.info("Elasticsearch instruments are not installable. Skipping.")
            return False

        self.__class__.installed = True

        self.instrument_client()
        self.instrument_transport()

    def uninstall(self):
        if not self.installed:
            logger.info("Elasticsearch instruments are not installed. Skipping.")
            return False

        self.uninstrument_client()
        self.uninstrument_transport()

        self.__class__.installed = False

    def instrument_client(self):
        for name in self.__class__.CLIENT_METHODS:
            method = getattr(Elasticsearch, name, None)
            if method is not None:
                setattr(Elasticsearch, name, wrap_client_method(method))

    def uninstrument_client(self):
        for name in self.__class__.CLIENT_METHODS:
            method = getattr(Elasticsearch, name, None)
            if method is not None:
                setattr(Elasticsearch, name, method.__wrapped__)

    def instrument_transport(self):
        try:

            def _sanitize_name(name):
                try:
                    op = name.split("/")[-1]
                    op = op[1:]  # chop leading '_' from op
                    allowed_names = [
                        "bench",
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
                        "search",
                    ]

                    if op in allowed_names:
                        return op.title()
                    return "Unknown"
                except Exception:
                    return "Unknown"

            @wrapt.decorator
            def wrapped_perform_request(wrapped, instance, args, kwargs):
                try:
                    op = _sanitize_name(args[1])
                except IndexError:
                    op = "Unknown"

                tracked_request = TrackedRequest.instance()
                tracked_request.start_span(
                    operation="Elasticsearch/{}".format(op), ignore_children=True
                )

                try:
                    return wrapped(*args, **kwargs)
                finally:
                    tracked_request.stop_span()

            Transport.perform_request = wrapped_perform_request(
                Transport.perform_request
            )

            logger.info("Instrumented Elasticsearch Transport")

        except Exception as e:
            logger.warning(
                "Unable to instrument for Elasticsearch Transport.perform_request: %r",
                e,
            )
            return False
        return True

    def uninstrument_transport(self):

        Transport.perform_request = Transport.perform_request.__wrapped__


@wrapt.decorator
def wrap_client_method(wrapped, instance, args, kwargs):
    def _get_index(index, *args, **kwargs):
        return index

    try:
        index = _get_index(*args, **kwargs)
    except TypeError:
        index = "Unknown"
    else:
        if not index:
            index = "Unknown"
        if isinstance(index, (list, tuple)):
            index = ",".join(index)
    index = index.title()
    camel_name = "".join(c.title() for c in wrapped.__name__.split("_"))
    operation = "Elasticsearch/{}/{}".format(index, camel_name)
    tracked_request = TrackedRequest.instance()
    tracked_request.start_span(operation=operation, ignore_children=True)

    try:
        return wrapped(*args, **kwargs)
    finally:
        tracked_request.stop_span()
