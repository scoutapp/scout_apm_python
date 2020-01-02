# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

import wrapt

from scout_apm.compat import get_function_argument_names
from scout_apm.core.tracked_request import TrackedRequest

try:
    from elasticsearch import Elasticsearch, Transport
except ImportError:  # pragma: no cover
    Elasticsearch = None
    Transport = None

logger = logging.getLogger(__name__)


def ensure_installed():
    logger.info("Ensuring elasticsearch instrumentation is installed.")

    if Elasticsearch is None:
        logger.info("Unable to import elasticsearch.Elasticsearch")
    else:
        ensure_client_instrumented()
        ensure_transport_instrumented()


CLIENT_METHODS = [
    "bulk",
    "clear_scroll",
    "count",
    "create",
    "delete",
    "delete_by_query",
    "delete_by_query_rethrottle",
    "delete_script",
    "exists",
    "exists_source",
    "explain",
    "field_caps",
    "get",
    "get_script",
    "get_source",
    "index",
    "info",
    "mget",
    "msearch",
    "msearch_template",
    "mtermvectors",
    "ping",
    "put_script",
    "rank_eval",
    "reindex",
    "reindex_rethrottle",
    "render_search_template",
    "scripts_painless_context",
    "scripts_painless_execute",
    "scroll",
    "search",
    "search_shards",
    "search_template",
    "termvectors",
    "update",
    "update_by_query",
    "update_by_query_rethrottle",
]


have_patched_client = False


def ensure_client_instrumented():
    global have_patched_client

    if not have_patched_client:
        for name in CLIENT_METHODS:
            try:
                method = getattr(Elasticsearch, name)
                if "index" in get_function_argument_names(method):
                    wrapped = wrap_client_index_method(method)
                else:
                    wrapped = wrap_client_method(method)
                setattr(Elasticsearch, name, wrapped)
            except Exception as exc:
                logger.warning(
                    "Unable to instrument elasticsearch.Elasticsearch.%s: %r",
                    name,
                    exc,
                    exc_info=exc,
                )

        have_patched_client = True


@wrapt.decorator
def wrap_client_index_method(wrapped, instance, args, kwargs):
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


@wrapt.decorator
def wrap_client_method(wrapped, instance, args, kwargs):
    camel_name = "".join(c.title() for c in wrapped.__name__.split("_"))
    operation = "Elasticsearch/{}".format(camel_name)
    tracked_request = TrackedRequest.instance()
    tracked_request.start_span(operation=operation, ignore_children=True)

    try:
        return wrapped(*args, **kwargs)
    finally:
        tracked_request.stop_span()


have_patched_transport = False


def ensure_transport_instrumented():
    global have_patched_transport

    if not have_patched_transport:
        try:
            Transport.perform_request = wrapped_perform_request(
                Transport.perform_request
            )
        except Exception as exc:
            logger.warning(
                "Unable to instrument elasticsearch.Transport.perform_request: %r",
                exc,
                exc_info=exc,
            )

    have_patched_transport = True


def _sanitize_name(name):
    try:
        op = name.split("/")[-1]
        op = op[1:]  # chop leading '_' from op
        known_names = (
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
        )
        if op in known_names:
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
