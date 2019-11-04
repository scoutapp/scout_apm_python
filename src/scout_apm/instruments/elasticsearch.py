# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

import wrapt

from scout_apm.core.tracked_request import TrackedRequest

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
        try:
            from elasticsearch import Elasticsearch  # noqa: F401
            from elasticsearch import Transport  # noqa: F401
        except ImportError:
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

        self.__class__.installed = False

        self.uninstrument_client()
        self.uninstrument_transport()

    def instrument_client(self):
        try:
            from elasticsearch import Elasticsearch  # noqa: F401
        except ImportError:
            logger.info(
                "Unable to import for Elasticsearch Client instruments. "
                "Instrument install failed."
            )
            return False

        for method_str in self.__class__.CLIENT_METHODS:
            try:
                code_str = """\
@wrapt.decorator
def wrapped_{method_str}(wrapped, instance, args, kwargs):
    tracked_request = TrackedRequest.instance()
    index = kwargs.get('index', 'Unknown')
    if isinstance(index, (list, tuple)):
        index = ','.join(index)
    index = index.title()
    name = '/'.join(['Elasticsearch', index, '{camel_name}'])
    tracked_request.start_span(operation=name, ignore_children=True)

    try:
        return wrapped(*args, **kwargs)
    finally:
        tracked_request.stop_span()


Elasticsearch.{method_str} = wrapped_{method_str}(Elasticsearch.{method_str})
""".format(
                    method_str=method_str,
                    camel_name="".join(c.title() for c in method_str.split("_")),
                )

                exec(code_str)
                logger.info("Instrumented Elasticsearch Elasticsearch.%s", method_str)

            except Exception as e:
                logger.warning(
                    "Unable to instrument for Elasticsearch Elasticsearch.%s: %r",
                    method_str,
                    e,
                )
                return False
        return True

    def uninstrument_client(self):
        from elasticsearch import Elasticsearch

        for method_str in self.__class__.CLIENT_METHODS:
            setattr(
                Elasticsearch,
                method_str,
                getattr(Elasticsearch, method_str).__wrapped__,
            )

    def instrument_transport(self):
        try:
            from elasticsearch import Transport

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
        from elasticsearch import Transport

        Transport.perform_request = Transport.perform_request.__wrapped__
