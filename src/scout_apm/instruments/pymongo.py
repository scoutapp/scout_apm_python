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


class Instrument(object):
    installed = False

    PYMONGO_METHODS = [
        "aggregate",
        "bulk_write",
        "count",
        "create_index",
        "create_indexes",
        "delete_many",
        "delete_one",
        "distinct",
        "drop",
        "drop_index",
        "drop_indexes",
        "ensure_index",
        "find_and_modify",
        "find_one",
        "find_one_and_delete",
        "find_one_and_replace",
        "find_one_and_update",
        "group",
        "inline_map_reduce",
        "insert",
        "insert_many",
        "insert_one",
        "map_reduce",
        "reindex",
        "remove",
        "rename",
        "replace_one",
        "save",
        "update",
        "update_many",
        "update_one",
    ]

    def installable(self):
        if Collection is None:
            logger.info("Unable to import for PyMongo instruments")
            return False
        if self.installed:
            logger.warning("PyMongo Instruments are already installed.")
            return False
        return True

    def install(self):
        if not self.installable():
            logger.info("PyMongo instruments are not installable. Skipping.")
            return False

        self.__class__.installed = True

        for name in self.__class__.PYMONGO_METHODS:
            method = getattr(Collection, name, None)
            if method is not None:
                setattr(Collection, name, wrap_collection_method(method))
        return True

    def uninstall(self):
        if not self.installed:
            logger.info("PyMongo instruments are not installed. Skipping.")
            return False

        for name in self.__class__.PYMONGO_METHODS:
            method = getattr(Collection, name, None)
            if method is not None:
                setattr(Collection, name, method.__wrapped__)

        self.__class__.installed = False


@wrapt.decorator
def wrap_collection_method(wrapped, instance, args, kwargs):
    tracked_request = TrackedRequest.instance()
    camel_name = "".join(c.title() for c in wrapped.__name__.split("_"))
    operation = "MongoDB/{}.{}".format(instance.name, camel_name)
    span = tracked_request.start_span(operation=operation, ignore_children=True)
    span.tag("name", instance.name)

    try:
        return wrapped(*args, **kwargs)
    finally:
        tracked_request.stop_span()
