from __future__ import absolute_import, division, print_function, unicode_literals

import logging

# Used in the exec() call below.
from scout_apm.core.monkey import monkeypatch_method, unpatch_method
from scout_apm.core.tracked_request import TrackedRequest

logger = logging.getLogger(__name__)


class Instrument(object):
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

    def __init__(self):
        self.installed = False

    def installable(self):
        try:
            from elasticsearch import Elasticsearch  # noqa: F401
            from elasticsearch import Transport  # noqa: F401
        except ImportError:
            logger.info("Unable to import for Elasticsearch instruments")
            return False
        if self.installed:
            logger.warn("Elasticsearch Instruments are already installed.")
            return False
        return True

    def install(self):
        if not self.installable():
            logger.info("Elasticsearch instruments are not installable. Skipping.")
            return False

        self.installed = True

        self.instrument_client()
        self.instrument_transport()

    def uninstall(self):
        if not self.installed:
            logger.info("Elasticsearch instruments are not installed. Skipping.")
            return False

        self.installed = False

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
@monkeypatch_method(Elasticsearch)
def {method_str}(original, self, *args, **kwargs):
    tr = TrackedRequest.instance()
    index = kwargs.get('index', 'Unknown')
    if isinstance(index, (list, tuple)):
        index = ','.join(index)
    index = index.title()
    name = '/'.join(['Elasticsearch', index, '{camel_name}'])
    tr.start_span(operation=name, ignore_children=True)


    try:
        return original(*args, **kwargs)
    finally:
        tr.stop_span()
""".format(
                    method_str=method_str,
                    camel_name="".join(c.title() for c in method_str.split("_")),
                )

                exec(code_str)
                logger.info("Instrumented Elasticsearch Elasticsearch.%s", method_str)

            except Exception as e:
                logger.warn(
                    "Unable to instrument for Elasticsearch Elasticsearch.%s: %r",
                    method_str,
                    e,
                )
                return False
        return True

    def uninstrument_client(self):
        from elasticsearch import Elasticsearch

        for method_str in self.__class__.CLIENT_METHODS:
            unpatch_method(Elasticsearch, method_str)

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

            @monkeypatch_method(Transport)
            def perform_request(original, self, *args, **kwargs):
                try:
                    op = _sanitize_name(args[1])
                except IndexError:
                    op = "Unknown"

                tr = TrackedRequest.instance()
                tr.start_span(
                    operation="Elasticsearch/{}".format(op), ignore_children=True
                )

                try:
                    return original(*args, **kwargs)
                finally:
                    tr.stop_span()

            logger.info("Instrumented Elasticsearch Transport")

        except Exception as e:
            logger.warn(
                "Unable to instrument for Elasticsearch Transport.perform_request: %r",
                e,
            )
            return False
        return True

    def uninstrument_transport(self):
        from elasticsearch import Transport

        unpatch_method(Transport, "perform_request")
