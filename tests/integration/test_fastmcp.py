# coding=utf-8

import sys
from contextlib import contextmanager

import pytest

from scout_apm.api import Config


def parse_version(v):
    """Parse a semantic version string into a tuple of integers."""
    return tuple(int(x) for x in v.split(".")[:3])


# Try to import fastMCP and check version
try:
    from fastmcp import FastMCP
    from fastmcp import __version__ as fastmcp_version
    from fastmcp.exceptions import ToolError

    from scout_apm.fastmcp import ScoutMiddleware
except (ImportError, TypeError):
    fastmcp_version = "0.0.0"

_fastmcp_version = parse_version(fastmcp_version)

pytestmark = pytest.mark.skipif(
    _fastmcp_version < (2, 13, 0) or sys.version_info < (3, 10),
    reason="These tests require fastMCP 2.13.0+ and Python 3.10+",
)


async def _call_tool(mcp, name, arguments):
    """
    Call a tool on a FastMCP server, compatible with both 2.x and 3.x.

    Returns (content_blocks, metadata) for uniform access.
    """
    if _fastmcp_version >= (3,):
        result = await mcp.call_tool(name, arguments)
        return result.content, result.meta
    else:
        return await mcp._call_tool_mcp(name, arguments)


async def _list_tools(mcp):
    """
    List tools on a FastMCP server, compatible with both 2.x and 3.x.
    """
    if _fastmcp_version >= (3,):
        return await mcp.list_tools()
    else:
        return await mcp._list_tools_mcp()


@contextmanager
def server_with_scout(scout_config=None):
    """
    Context manager that configures and installs Scout instrumentation
    for a FastMCP server.
    """
    if scout_config is None:
        scout_config = {}

    scout_config["core_agent_launch"] = False
    scout_config.setdefault("monitor", True)

    # Create FastMCP server
    mcp = FastMCP(name="TestServer")

    # Configure Scout
    Config.set(**scout_config)

    # Add Scout middleware
    mcp.add_middleware(ScoutMiddleware())

    try:
        yield mcp
    finally:
        Config.reset_all()


async def test_basic_tool_instrumentation(tracked_requests):
    """Test that basic tool execution is tracked."""
    with server_with_scout() as mcp:

        @mcp.tool
        def add_numbers(a: int, b: int) -> int:
            """Add two numbers together."""
            return a + b

        # Verify tool is registered
        tools_list = await _list_tools(mcp)
        assert len(tools_list) == 1
        assert tools_list[0].name == "add_numbers"

        # Simulate tool execution using the MCP protocol method
        content_blocks, metadata = await _call_tool(
            mcp, "add_numbers", {"a": 5, "b": 3}
        )
        assert len(content_blocks) == 1
        assert content_blocks[0].text == "8"

    # Verify tracking
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.operation == "Controller/add_numbers"
    assert tracked_request.is_real_request is True
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.complete_spans[0].operation == "Controller/add_numbers"


async def test_async_tool_instrumentation(tracked_requests):
    """Test that async tool execution is tracked."""
    with server_with_scout() as mcp:

        @mcp.tool
        async def async_multiply(a: int, b: int) -> int:
            """Multiply two numbers asynchronously."""
            return a * b

        # Simulate tool execution
        content_blocks, metadata = await _call_tool(
            mcp, "async_multiply", {"a": 4, "b": 7}
        )
        assert content_blocks[0].text == "28"

    # Verify tracking
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.operation == "Controller/async_multiply"
    assert tracked_request.is_real_request is True


async def test_tool_with_metadata(tracked_requests):
    """Test that tool metadata (tags, annotations, meta) is captured."""
    with server_with_scout() as mcp:

        @mcp.tool(
            name="search_db",
            description="Search the database for records",
            tags={"database", "search"},
            annotations={
                "readOnlyHint": True,
                "idempotentHint": True,
                "openWorldHint": False,
            },
            meta={"version": "1.0", "author": "test-team"},
        )
        def search_database(query: str) -> list:
            """Search implementation."""
            return [{"id": 1, "name": "result"}]

        # Execute tool
        content_blocks, metadata = await _call_tool(mcp, "search_db", {"query": "test"})
        assert len(content_blocks) == 1

    # Verify metadata tags
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.operation == "Controller/search_db"

    tags = tracked_request.tags
    assert "tool_description" in tags
    assert "Search the database" in tags["tool_description"]
    assert tags.get("tool_tags") == "database,search"
    assert tags.get("read_only") is True
    assert tags.get("idempotent") is True
    assert tags.get("external") is False
    assert tags.get("tool_meta") == "{'version': '1.0', 'author': 'test-team'}"


async def test_tool_with_arguments(tracked_requests):
    """Test that tool arguments are captured and filtered."""
    with server_with_scout() as mcp:

        @mcp.tool
        def process_data(data: str, password: str, count: int) -> dict:
            """Process data with sensitive parameters."""
            return {"processed": True, "length": len(data)}

        # Execute tool with sensitive parameter
        content_blocks, metadata = await _call_tool(
            mcp,
            "process_data",
            {"data": "test data", "password": "secret123", "count": 5},
        )
        # FastMCP returns list of ContentBlock, need to parse the JSON
        import json

        result_data = json.loads(content_blocks[0].text)
        assert result_data["processed"] is True

    # Verify arguments are tagged
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]

    # Check that arguments tag exists
    assert "arguments" in tracked_request.tags
    args_str = tracked_request.tags["arguments"]

    # Verify password is filtered
    assert "secret123" not in args_str
    assert "[FILTERED]" in args_str
    # Non-sensitive data should be present
    assert "test data" in args_str


async def test_tool_error_tracking(tracked_requests):
    """Test that tool errors are tracked properly."""
    with server_with_scout() as mcp:

        @mcp.tool
        def divide_numbers(a: float, b: float) -> float:
            """Divide two numbers."""
            if b == 0:
                raise ValueError("Division by zero")
            return a / b

        # Execute tool that raises an error
        with pytest.raises(ToolError, match="Division by zero"):
            await _call_tool(mcp, "divide_numbers", {"a": 10, "b": 0})

    # Verify error tracking
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.operation == "Controller/divide_numbers"
    assert tracked_request.tags.get("error") == "true"


async def test_multiple_tool_calls(tracked_requests):
    """Test that multiple tool calls create separate tracked requests."""
    with server_with_scout() as mcp:

        @mcp.tool
        def echo(message: str) -> str:
            """Echo the message."""
            return message

        # Execute multiple times
        await _call_tool(mcp, "echo", {"message": "first"})
        await _call_tool(mcp, "echo", {"message": "second"})
        await _call_tool(mcp, "echo", {"message": "third"})

    # Should have 3 separate tracked requests
    assert len(tracked_requests) == 3
    for tracked_request in tracked_requests:
        assert tracked_request.operation == "Controller/echo"
        assert tracked_request.is_real_request is True


async def test_no_monitor(tracked_requests):
    """Test that instrumentation is disabled when monitor=False."""
    with server_with_scout(scout_config={"monitor": False}) as mcp:

        @mcp.tool
        def monitored_tool() -> str:
            """This should not be tracked."""
            return "result"

        content_blocks, metadata = await _call_tool(mcp, "monitored_tool", {})
        assert content_blocks[0].text == "result"

    # Should not track when monitor is disabled
    assert len(tracked_requests) == 0
