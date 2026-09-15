# coding=utf-8

import logging

import scout_apm.core
from scout_apm.core.error import ErrorMonitor
from scout_apm.core.tracked_request import TrackedRequest
from scout_apm.core.web_requests import filter_element

try:
    from fastmcp.server.middleware import Middleware, MiddlewareContext
except ImportError:
    Middleware = None
    MiddlewareContext = None

logger = logging.getLogger(__name__)


class ScoutMiddleware(Middleware if Middleware is not None else object):
    """
    FastMCP middleware for Scout APM instrumentation.

    This middleware tracks tool executions and collects performance metrics
    for FastMCP servers.
    """

    def __init__(self):
        if Middleware is not None:
            super().__init__()
        installed = scout_apm.core.install()
        self._do_nothing = not installed

    async def on_call_tool(self, context, call_next):
        """
        Track tool execution with Scout APM.

        This hook is called whenever a tool is executed. We create a
        TrackedRequest for each tool invocation to measure performance
        and capture errors.
        """
        if self._do_nothing:
            return await call_next(context)

        tracked_request = TrackedRequest.instance()
        tracked_request.is_real_request = True

        # Get tool name from execution context
        tool_name = getattr(context.message, "name", "unknown")
        operation = f"Controller/{tool_name}"
        tracked_request.operation = operation

        # Add rich metadata from tool object via context
        try:
            tool = await context.fastmcp_context.fastmcp.get_tool(tool_name)
            if tool is not None:
                self._tag_tool_metadata(tracked_request, tool)
        except Exception as exc:
            # Tool not found or other error - continue without metadata
            logger.warning(f"Unable to fetch tool metadata for {tool_name}: {exc}")

        # Tag tool arguments (filtered for sensitive data)
        arguments = getattr(context.message, "arguments", {})
        if arguments:
            filtered_args = filter_element("", arguments)
            tracked_request.tag("arguments", str(filtered_args))

        with tracked_request.span(operation=operation, should_capture_backtrace=False):
            try:
                result = await call_next(context)
                return result
            except Exception as exc:
                tracked_request.tag("error", "true")
                ErrorMonitor.send(
                    (type(exc), exc, exc.__traceback__),
                    custom_controller=operation,
                    custom_params={"tool": tool_name, "arguments": arguments},
                )
                raise

    @staticmethod
    def _annotation_hint(annotations, snake_name, camel_name, default):
        """Read a single MCP tool-annotation hint across SDK versions.

        Supports both dict-style annotations and object/pydantic-model style,
        and both the snake_case (MCP SDK v2 / FastMCP 4.x) and camelCase
        (MCP SDK v1 / FastMCP 2.x-3.x) field names. Every access is guarded so
        a deprecated-and-raising or missing field never propagates.
        """
        if isinstance(annotations, dict):
            for key in (snake_name, camel_name):
                if key in annotations:
                    return annotations[key]
            return default
        for name in (snake_name, camel_name):
            try:
                if hasattr(annotations, name):
                    return getattr(annotations, name)
            except Exception:  # noqa: BLE001 -- never let a bad field escape
                continue
        return default

    def _tag_tool_metadata(self, tracked_request, tool):
        """
        Add rich tool metadata as tags to the tracked request.

        This extracts metadata from the FastMCP tool object and adds it
        as tags for filtering and analysis in Scout APM.
        https://gofastmcp.com/servers/tools#decorator-arguments
        """
        # Add tool description (truncated)
        if hasattr(tool, "description") and tool.description:
            tracked_request.tag("tool_description", str(tool.description)[:200])

        if hasattr(tool, "tags") and tool.tags:
            tracked_request.tag("tool_tags", ",".join(sorted(tool.tags)))

        # Add behavioral annotations (dict and object-style).
        # https://gofastmcp.com/servers/tools#param-annotations
        #
        # The hint field names differ across MCP SDK / FastMCP versions:
        #   * FastMCP 2.x / 3.x (MCP SDK v1): camelCase -- readOnlyHint, etc.
        #   * FastMCP 4.x       (MCP SDK v2): snake_case -- read_only_hint, etc.
        # In v2 the old camelCase attributes still "exist" (hasattr is True) but
        # accessing them raises a deprecation error, so we must read snake_case
        # first and only fall back to camelCase, guarding every access so a
        # renamed/removed field can never raise out of the instrumentation.
        if hasattr(tool, "annotations") and tool.annotations:
            annotations = tool.annotations
            for tag_name, snake, camel, default in (
                ("read_only", "read_only_hint", "readOnlyHint", False),
                ("destructive", "destructive_hint", "destructiveHint", False),
                ("idempotent", "idempotent_hint", "idempotentHint", False),
                ("external", "open_world_hint", "openWorldHint", True),
            ):
                value = self._annotation_hint(annotations, snake, camel, default)
                tracked_request.tag(tag_name, value)

        if hasattr(tool, "meta") and tool.meta:
            tracked_request.tag("tool_meta", str(tool.meta))
