# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

import wrapt

from scout_apm.core.tracked_request import TrackedRequest

try:
    from pymongo.collection import Collection
except ImportError:
    Collection = None

logger = logging.getLogger(__name__)

have_patched_collection = False


def ensure_installed():
    global have_patched_collection

    logger.debug("Instrumenting pymongo.")

    if Collection is None:
        logger.debug("Couldn't import pymongo.Collection - probably not installed.")
    elif not have_patched_collection:
        for name in COLLECTION_METHODS:
            try:
                setattr(
                    Collection, name, wrap_collection_method(getattr(Collection, name))
                )
            except Exception as exc:
                logger.warning(
                    "Failed to instrument pymongo.Collection.%s: %r",
                    name,
                    exc,
                    exc_info=exc,
                )
        have_patched_collection = True


COLLECTION_METHODS = [
    "aggregate",
    "aggregate_raw_batches",
    "bulk_write",
    "count",
    "count_documents",
    "create_index",
    "create_indexes",
    "delete_many",
    "delete_one",
    "distinct",
    "drop",
    "drop_index",
    "drop_indexes",
    "ensure_index",
    "estimated_document_count",
    "find",
    "find_and_modify",
    "find_one",
    "find_one_and_delete",
    "find_one_and_replace",
    "find_one_and_update",
    "find_raw_batches",
    "group",
    "index_information",
    "inline_map_reduce",
    "insert",
    "insert_many",
    "insert_one",
    "list_indexes",
    "map_reduce",
    "parallel_scan",
    "reindex",
    "remove",
    "rename",
    "replace_one",
    "save",
    "update",
    "update_many",
    "update_one",
]


@wrapt.decorator
def wrap_collection_method(wrapped, instance, args, kwargs):
    tracked_request = TrackedRequest.instance()
    camel_name = "".join(c.title() for c in wrapped.__name__.split("_"))
    operation = "MongoDB/{}.{}".format(instance.name, camel_name)
    with tracked_request.span(operation=operation, ignore_children=True) as span:
        span.tag("name", instance.name)
        return wrapped(*args, **kwargs)
