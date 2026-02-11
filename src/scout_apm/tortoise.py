# coding=utf-8

import functools
import logging

from scout_apm.core.tracked_request import TrackedRequest

logger = logging.getLogger(__name__)

# Methods that always have their own SQL execution path on every backend.
_ALWAYS_PATCH = {
    "execute_insert": ("SQL/Query", False),
    "execute_query": ("SQL/Query", False),
    "execute_many": ("SQL/Many", True),
}

# Methods that may delegate to execute_query in the base class.
# Only patch these when the backend class defines them directly,
# otherwise instrumenting execute_query already covers them.
_PATCH_IF_OWN = {
    "execute_query_dict": ("SQL/Query", False),
    "execute_query_dict_with_affected": ("SQL/Query", False),
    "execute_script": ("SQL/Query", False),
}


def instrument_tortoise():
    """
    Instrument all active Tortoise ORM database connections for Scout APM.

    Must be called after ``Tortoise.init()``.
    """
    from tortoise.connection import get_connections

    seen_classes = set()
    for conn in get_connections().all():
        cls = type(conn)
        if cls not in seen_classes:
            seen_classes.add(cls)
            _patch_client_class(cls)


def _patch_client_class(cls):
    if getattr(cls, "_scout_instrumented", False):
        return

    for method_name, (operation, is_many) in _ALWAYS_PATCH.items():
        if hasattr(cls, method_name):
            original = getattr(cls, method_name)
            setattr(cls, method_name, _make_async_wrapper(original, operation, is_many))

    for method_name, (operation, is_many) in _PATCH_IF_OWN.items():
        if method_name in cls.__dict__:
            original = getattr(cls, method_name)
            setattr(cls, method_name, _make_async_wrapper(original, operation, is_many))

    cls._scout_instrumented = True


def _make_async_wrapper(original, operation, is_many):
    @functools.wraps(original)
    async def wrapper(self, *args, **kwargs):
        tracked_request = TrackedRequest.instance()
        span = tracked_request.start_span(operation=operation)

        # First positional arg is always the query string.
        query = args[0] if args else kwargs.get("query", "")
        span.tag("db.statement", query)

        try:
            return await original(self, *args, **kwargs)
        finally:
            if is_many:
                # For execute_many, second arg is the list of value sets.
                values = args[1] if len(args) > 1 else kwargs.get("values", [])
                count = len(values)
            else:
                count = 1
            if tracked_request.n_plus_one_tracker.should_capture_backtrace(
                sql=query,
                duration=span.duration(),
                count=count,
            ):
                span.capture_backtrace()
            tracked_request.stop_span()

    return wrapper
