# coding=utf-8

import sys
from unittest import mock

import pytest

from scout_apm.core.tracked_request import TrackedRequest

# Skip all fastMCP tests for Python < 3.10 since fastMCP requires Python 3.10+
pytestmark = pytest.mark.skipif(
    sys.version_info < (3, 10), reason="fastMCP requires Python 3.10 or higher"
)


class TestScoutMiddleware:
    """Unit tests for ScoutMiddleware without requiring fastmcp."""

    def test_middleware_not_available(self):
        """Test behavior when fastmcp is not installed."""
        # Temporarily hide fastmcp
        with mock.patch.dict(sys.modules, {"fastmcp.server.middleware": None}):
            # Reimport to trigger ImportError handling
            import importlib

            import scout_apm.fastmcp

            importlib.reload(scout_apm.fastmcp)

            from scout_apm.fastmcp import ScoutMiddleware

            middleware = ScoutMiddleware()
            assert middleware._do_nothing  # Should disable itself

    def test_tag_tool_metadata_with_dict_annotations(self):
        """Test _tag_tool_metadata with dict-style annotations."""
        from scout_apm.fastmcp import ScoutMiddleware

        middleware = ScoutMiddleware()
        tracked_request = mock.Mock(spec=TrackedRequest)

        # Create mock tool with dict-style annotations
        mock_tool = mock.Mock()
        mock_tool.description = "Test tool description"
        mock_tool.tags = {"tag1", "tag2", "tag3"}
        mock_tool.annotations = {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
        mock_tool.meta = {"version": "2.0", "author": "test-author"}

        middleware._tag_tool_metadata(tracked_request, mock_tool)

        # Verify tags were called
        calls = [call[0] for call in tracked_request.tag.call_args_list]
        assert ("tool_description", "Test tool description") in calls
        assert any("tool_tags" in call for call in calls)
        assert ("read_only", True) in calls
        assert ("destructive", False) in calls
        assert ("idempotent", True) in calls
        assert ("external", False) in calls
        assert ("tool_meta", "{'version': '2.0', 'author': 'test-author'}") in calls

    def test_tag_tool_metadata_with_object_annotations(self):
        """Test _tag_tool_metadata with object-style annotations."""
        from scout_apm.fastmcp import ScoutMiddleware

        middleware = ScoutMiddleware()
        tracked_request = mock.Mock(spec=TrackedRequest)

        # Create mock tool with object-style annotations
        mock_tool = mock.Mock()
        mock_tool.description = "Another test"
        mock_tool.tags = set()
        mock_annotations = mock.Mock()
        mock_annotations.readOnlyHint = False
        mock_annotations.destructiveHint = True
        mock_annotations.idempotentHint = False
        mock_annotations.openWorldHint = True
        mock_tool.annotations = mock_annotations
        mock_tool.meta = {}

        middleware._tag_tool_metadata(tracked_request, mock_tool)

        # Verify object-style access worked
        calls = [call[0] for call in tracked_request.tag.call_args_list]
        assert ("read_only", False) in calls
        assert ("destructive", True) in calls
        assert ("idempotent", False) in calls
        assert ("external", True) in calls

    def test_tag_tool_metadata_with_missing_fields(self):
        """Test _tag_tool_metadata handles missing fields gracefully."""
        from scout_apm.fastmcp import ScoutMiddleware

        middleware = ScoutMiddleware()
        tracked_request = mock.Mock(spec=TrackedRequest)

        # Create minimal mock tool with no optional fields
        mock_tool = mock.Mock(spec=[])

        # Should not raise exceptions
        middleware._tag_tool_metadata(tracked_request, mock_tool)

        # Should not have called tag at all
        tracked_request.tag.assert_not_called()

    def test_tag_tool_metadata_truncates_description(self):
        """Test that long descriptions are truncated."""
        from scout_apm.fastmcp import ScoutMiddleware

        middleware = ScoutMiddleware()
        tracked_request = mock.Mock(spec=TrackedRequest)

        # Create tool with very long description
        mock_tool = mock.Mock()
        mock_tool.description = "x" * 500  # 500 characters
        mock_tool.tags = set()
        mock_tool.annotations = None
        mock_tool.meta = None

        middleware._tag_tool_metadata(tracked_request, mock_tool)

        # Verify description was truncated to 200 chars
        calls = tracked_request.tag.call_args_list
        desc_call = [call for call in calls if call[0][0] == "tool_description"][0]
        assert len(desc_call[0][1]) == 200

    @pytest.mark.asyncio
    async def test_on_call_tool_with_exception(self):
        """Test that exceptions in tools are properly tracked."""
        from scout_apm.fastmcp import ScoutMiddleware

        middleware = ScoutMiddleware()
        middleware._do_nothing = False

        mock_context = mock.Mock()
        mock_context.message = mock.Mock()
        mock_context.message.name = "failing_tool"
        mock_context.message.arguments = {"arg": "value"}
        mock_context.fastmcp_context = None  # No metadata fetching needed for this test

        # Mock call_next to raise an exception
        async def failing_call_next(ctx):
            raise ValueError("Tool failed")

        # Mock TrackedRequest
        mock_tracked = mock.Mock(spec=TrackedRequest)
        mock_tracked.span.return_value = mock.MagicMock()

        with mock.patch(
            "scout_apm.fastmcp.TrackedRequest.instance", return_value=mock_tracked
        ):
            with pytest.raises(ValueError, match="Tool failed"):
                await middleware.on_call_tool(mock_context, failing_call_next)

            # Verify error was tagged
            mock_tracked.tag.assert_any_call("error", "true")

    @pytest.mark.asyncio
    async def test_on_call_tool_skips_when_disabled(self):
        """Test that on_call_tool does nothing when _do_nothing is True."""
        from scout_apm.fastmcp import ScoutMiddleware

        middleware = ScoutMiddleware()
        middleware._do_nothing = True

        mock_context = mock.Mock()
        expected_result = {"result": "value"}

        async def mock_call_next(ctx):
            return expected_result

        # Should just pass through without tracking
        result = await middleware.on_call_tool(mock_context, mock_call_next)

        assert result == expected_result

    @pytest.mark.asyncio
    async def test_on_call_tool_fetches_metadata_from_context(self):
        """Test that on_call_tool fetches tool metadata from context."""
        from scout_apm.fastmcp import ScoutMiddleware

        middleware = ScoutMiddleware()
        middleware._do_nothing = False

        # Mock tool with metadata
        mock_tool = mock.Mock()
        mock_tool.description = "Test tool"
        mock_tool.tags = {"tag1", "tag2"}
        mock_tool.annotations = None
        mock_tool.meta = None

        # Mock fastmcp.get_tool to return our tool
        mock_fastmcp = mock.Mock()
        mock_fastmcp.get_tool = mock.AsyncMock(return_value=mock_tool)

        # Mock context with fastmcp_context
        mock_fastmcp_context = mock.Mock()
        mock_fastmcp_context.fastmcp = mock_fastmcp

        mock_context = mock.Mock()
        mock_context.fastmcp_context = mock_fastmcp_context
        mock_context.message = mock.Mock()
        mock_context.message.name = "test_tool"
        mock_context.message.arguments = {}

        async def mock_call_next(ctx):
            return {"result": "success"}

        # Mock TrackedRequest
        mock_tracked = mock.Mock(spec=TrackedRequest)
        mock_tracked.span.return_value = mock.MagicMock()

        with mock.patch(
            "scout_apm.fastmcp.TrackedRequest.instance", return_value=mock_tracked
        ):
            await middleware.on_call_tool(mock_context, mock_call_next)

        # Verify get_tool was called
        mock_fastmcp.get_tool.assert_called_once_with("test_tool")

        # Verify metadata was tagged
        tag_calls = [call[0] for call in mock_tracked.tag.call_args_list]
        assert any("tool_description" in call for call in tag_calls)
        assert any("tool_tags" in call for call in tag_calls)
