# coding=utf-8

import logging
from inspect import iscoroutinefunction

from scout_apm.core.tracked_request import TrackedRequest

try:
    from ariadne.asgi.handlers import GraphQLHTTPHandler
    from ariadne.types import Extension
except ImportError:  # pragma: no cover
    GraphQLHTTPHandler = None
    Extension = None

logger = logging.getLogger(__name__)


have_patched_handler_init = False


def ensure_installed():
    global have_patched_handler_init

    logger.debug("Instrumenting Ariadne.")

    if GraphQLHTTPHandler is None or Extension is None:
        logger.debug(
            "Couldn't import ariadne.asgi.handlers.GraphQLHTTPHandler or "
            "ariadne.types.Extension - probably not installed."
        )
        return

    if not have_patched_handler_init:
        try:
            GraphQLHTTPHandler.__init__ = wrapped_handler_init(
                GraphQLHTTPHandler.__init__
            )
        except Exception as exc:
            logger.warning(
                "Failed to instrument ariadne.asgi.handlers.GraphQLHTTPHandler.__init__"
                ": %r",
                exc,
                exc_info=exc,
            )
        else:
            have_patched_handler_init = True


def wrapped_handler_init(wrapped):
    """Install a Scout extension into every GraphQLHTTPHandler instance.

    Ariadne's HTTP handler takes an ``extensions=`` kwarg that is either a
    list of ``Extension`` types/factories or a callable returning that list
    per request. We coerce whatever the user passed into a per-request
    callable that always appends our ScoutExtension.
    """

    def init(self, *args, **kwargs):
        wrapped(self, *args, **kwargs)
        existing = self.extensions
        self.extensions = _compose_extensions(existing)

    init.__wrapped__ = wrapped
    return init


def _compose_extensions(existing):
    """Return a per-request extensions callable that includes ScoutExtension.

    Ariadne accepts three shapes for ``extensions``: ``None``, a list of
    ``Extension`` types/factories, or a callable ``(request, context)``
    returning either of the previous shapes (optionally awaitable).
    """
    if existing is None:
        return lambda request, context: [ScoutExtension]

    if callable(existing) and not isinstance(existing, type):
        # User supplied a callable; chain into it and append.
        def chained(request, context):
            result = existing(request, context)
            return _append_scout(result)

        return chained

    # User supplied a static list — append ourselves once.
    return list(existing) + [ScoutExtension]


def _append_scout(result):
    from inspect import isawaitable

    if isawaitable(result):

        async def awaited():
            inner = await result
            return list(inner or []) + [ScoutExtension]

        return awaited()
    return list(result or []) + [ScoutExtension]


if Extension is not None:

    class ScoutExtension(Extension):
        """Ariadne extension that records Scout APM spans and tags.

        Wraps the top-level resolver of every GraphQL request in a
        ``GraphQL/<ParentType>/<field>`` span (e.g. ``GraphQL/Query/login``,
        ``GraphQL/Mutation/createAccount``) and promotes that operation
        name to the parent ``Controller/...`` span and tracked request so
        the request shows up under a meaningful name in Scout.

        Nested resolver calls (e.g. resolving each field on the User type
        returned by ``login``) are intentionally not given their own
        spans: silkbraid-sized schemas can have hundreds of nested
        resolves per request and a span per resolve would explode the
        trace.
        """

        def __init__(self):
            self._operation_recorded = False

        def request_started(self, context):
            tracked_request = TrackedRequest.instance()
            tracked_request.is_real_request = True

        def resolve(self, next_, obj, info, **kwargs):
            # Only the top-level fields get their own span. The path's
            # ``prev`` attribute is None at the root, set to the parent
            # path for nested fields.
            if getattr(info.path, "prev", None) is not None:
                return next_(obj, info, **kwargs)

            operation = _operation_name(info)

            tracked_request = TrackedRequest.instance()
            tracked_request.is_real_request = True
            if not self._operation_recorded:
                # Rename the surrounding Controller span (typically set by
                # the ASGI middleware to e.g. ``Controller/ariadne...``)
                # so the transaction shows up by the GraphQL operation.
                tracked_request.operation = operation
                for span in tracked_request.active_spans:
                    if span.operation and span.operation.startswith("Controller/"):
                        span.operation = operation
                op_name = _client_operation_name(info)
                if op_name:
                    tracked_request.tag("graphql_operation_name", op_name)
                self._operation_recorded = True

            if iscoroutinefunction(next_):

                async def resolve_async():
                    with tracked_request.span(operation=operation):
                        return await next_(obj, info, **kwargs)

                return resolve_async()

            with tracked_request.span(operation=operation):
                return next_(obj, info, **kwargs)

        def has_errors(self, errors, context):
            TrackedRequest.instance().tag("error", "true")


def _operation_name(info):
    parent_type = getattr(info, "parent_type", None)
    parent_name = getattr(parent_type, "name", None) or "Unknown"
    field_name = getattr(info, "field_name", None) or "Unknown"
    return "GraphQL/{}/{}".format(parent_name, field_name)


def _client_operation_name(info):
    operation = getattr(info, "operation", None)
    name = getattr(operation, "name", None)
    return getattr(name, "value", None)
