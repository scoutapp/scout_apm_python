# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
from collections import namedtuple

import wrapt

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


ClientMethod = namedtuple("ClientMethod", ["name", "takes_index_argument"])

CLIENT_METHODS = [
    ClientMethod("bulk", True),
    ClientMethod("clear_scroll", False),
    ClientMethod("count", True),
    ClientMethod("create", True),
    ClientMethod("delete", True),
    ClientMethod("delete_by_query", True),
    ClientMethod("delete_by_query_rethrottle", False),
    ClientMethod("delete_script", False),
    ClientMethod("exists", True),
    ClientMethod("exists_source", True),
    ClientMethod("explain", True),
    ClientMethod("field_caps", True),
    ClientMethod("get", True),
    ClientMethod("get_script", False),
    ClientMethod("get_source", True),
    ClientMethod("index", True),
    ClientMethod("info", False),
    ClientMethod("mget", True),
    ClientMethod("msearch", True),
    ClientMethod("msearch_template", True),
    ClientMethod("mtermvectors", True),
    ClientMethod("ping", False),
    ClientMethod("put_script", False),
    ClientMethod("rank_eval", True),
    ClientMethod("reindex", False),
    ClientMethod("reindex_rethrottle", False),
    ClientMethod("render_search_template", False),
    ClientMethod("scripts_painless_context", False),
    ClientMethod("scripts_painless_execute", False),
    ClientMethod("scroll", False),
    ClientMethod("search", True),
    ClientMethod("search_shards", True),
    ClientMethod("search_template", True),
    ClientMethod("termvectors", True),
    ClientMethod("update", True),
    ClientMethod("update_by_query", True),
    ClientMethod("update_by_query_rethrottle", False),
]


have_patched_client = False


def ensure_client_instrumented():
    global have_patched_client

    if not have_patched_client:
        for name, takes_index_argument in CLIENT_METHODS:
            try:
                method = getattr(Elasticsearch, name)
                if takes_index_argument:
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
