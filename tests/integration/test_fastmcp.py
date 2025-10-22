# coding=utf-8

import sys
from contextlib import contextmanager

import pytest
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from scout_apm.api import Config
from scout_apm.fastmcp import ScoutMiddleware

# Skip all fastMCP tests for Python < 3.10 since fastMCP requires Python 3.10+
pytestmark = pytest.mark.skipif(
    sys.version_info < (3, 10), reason="fastMCP requires Python 3.10 or higher"
)


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

        # Simulate tool list request (caches metadata)
        tools_list = await mcp._list_tools()
        assert len(tools_list) == 1
        assert tools_list[0].key == "add_numbers"

        # Simulate tool execution using the MCP protocol method
        result = await mcp._mcp_call_tool("add_numbers", {"a": 5, "b": 3})
        # result is a tuple: (content_blocks, metadata)
        content_blocks, metadata = result
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
        result, metadata = await mcp._mcp_call_tool("async_multiply", {"a": 4, "b": 7})
        assert result[0].text == "28"

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

        # Cache metadata by listing tools
        await mcp._list_tools()

        # Execute tool
        result, metadata = await mcp._mcp_call_tool("search_db", {"query": "test"})
        assert len(result) == 1

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
        result, metadata = await mcp._mcp_call_tool(
            "process_data", {"data": "test data", "password": "secret123", "count": 5}
        )
        # FastMCP returns list of ContentBlock, need to parse the JSON
        import json

        result_data = json.loads(result[0].text)
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
            await mcp._mcp_call_tool("divide_numbers", {"a": 10, "b": 0})

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
        await mcp._mcp_call_tool("echo", {"message": "first"})
        await mcp._mcp_call_tool("echo", {"message": "second"})
        await mcp._mcp_call_tool("echo", {"message": "third"})

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

        result, metadata = await mcp._mcp_call_tool("monitored_tool", {})
        assert result[0].text == "result"

    # Should not track when monitor is disabled
    assert len(tracked_requests) == 0


async def test_tool_without_metadata_cache(tracked_requests):
    """Test that tools work even if metadata hasn't been cached."""
    with server_with_scout() as mcp:

        @mcp.tool
        def uncached_tool(value: int) -> int:
            """This tool is called without listing first."""
            return value * 2

        # Call tool without listing first (no metadata cache)
        result, metadata = await mcp._mcp_call_tool("uncached_tool", {"value": 21})
        assert result[0].text == "42"

    # Should still track the execution
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.operation == "Controller/uncached_tool"
    # Metadata tags won't be present, but basic tracking should work
    assert "tool_tags" not in tracked_request.tags
