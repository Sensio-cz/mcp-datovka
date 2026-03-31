"""Tests for MCP tool registration and parameter handling."""

import json
import pytest
from unittest.mock import patch, MagicMock

from mcp_datovka.config import BoxConfig


# Helpers for mocking
def _mock_box(alias="test-box", box_id="abc1234"):
    return BoxConfig(alias=alias, box_id=box_id, username="user", password="pass")


class TestSendMessageFilesParameter:
    """Test that files parameter accepts both str and list (MCP SDK compatibility)."""

    @patch("mcp_datovka.tools.datovka.get_box")
    def test_files_as_json_string(self, mock_get_box):
        mock_get_box.return_value = _mock_box()

        from mcp_datovka.tools.datovka import register_tools
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        register_tools(mcp)

        # Find the send tool function
        tools = {t.name: t for t in mcp._tool_manager._tools.values()}
        send_tool = tools.get("datovka_send_message")
        assert send_tool is not None

    @patch("mcp_datovka.tools.datovka.get_box")
    def test_files_preview_with_string(self, mock_get_box):
        """Test preview (confirmed=false) with files as JSON string."""
        mock_get_box.return_value = _mock_box()

        # Import the inner function by registering tools
        from mcp_datovka.tools.datovka import register_tools
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        register_tools(mcp)

        # Get the raw function
        fn = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "datovka_send_message":
                fn = tool.fn
                break

        files_str = json.dumps([{"filename": "test.xml", "mime_type": "text/xml", "content_base64": "dGVzdA=="}])
        result = json.loads(fn(
            from_box_alias="test-box",
            to_box_id="xyz9999",
            subject="Test",
            files=files_str,
            confirmed=False,
        ))
        assert result["status"] == "awaiting_confirmation"
        assert len(result["attachments"]) == 1
        assert result["attachments"][0]["filename"] == "test.xml"

    @patch("mcp_datovka.tools.datovka.get_box")
    def test_files_preview_with_list(self, mock_get_box):
        """Test preview (confirmed=false) with files as parsed list (MCP SDK behavior)."""
        mock_get_box.return_value = _mock_box()

        from mcp_datovka.tools.datovka import register_tools
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        register_tools(mcp)

        fn = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "datovka_send_message":
                fn = tool.fn
                break

        files_list = [{"filename": "test.pdf", "mime_type": "application/pdf", "content_base64": "dGVzdA=="}]
        result = json.loads(fn(
            from_box_alias="test-box",
            to_box_id="xyz9999",
            subject="Test",
            files=files_list,
            confirmed=False,
        ))
        assert result["status"] == "awaiting_confirmation"
        assert result["attachments"][0]["filename"] == "test.pdf"

    @patch("mcp_datovka.tools.datovka.get_box")
    def test_box_not_found(self, mock_get_box):
        mock_get_box.return_value = None

        from mcp_datovka.tools.datovka import register_tools
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        register_tools(mcp)

        fn = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "datovka_send_message":
                fn = tool.fn
                break

        result = json.loads(fn(
            from_box_alias="nonexistent",
            to_box_id="xyz9999",
            subject="Test",
            confirmed=False,
        ))
        assert "error" in result


class TestListBoxes:
    @patch("mcp_datovka.tools.datovka.get_boxes")
    def test_list_boxes(self, mock_get_boxes):
        mock_get_boxes.return_value = [
            _mock_box("box-a", "aaa1111"),
            _mock_box("box-b", "bbb2222"),
        ]

        from mcp_datovka.tools.datovka import register_tools
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        register_tools(mcp)

        fn = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "datovka_list_boxes":
                fn = tool.fn
                break

        result = json.loads(fn())
        assert len(result) == 2
        assert result[0]["alias"] == "box-a"
        assert result[1]["box_id"] == "bbb2222"


class TestSearchBox:
    @patch("mcp_datovka.tools.datovka.get_boxes")
    @patch("mcp_datovka.tools.datovka.get_box")
    def test_search_uses_first_box_when_no_alias(self, mock_get_box, mock_get_boxes):
        box = _mock_box()
        mock_get_box.return_value = None
        mock_get_boxes.return_value = [box]

        from mcp_datovka.tools.datovka import register_tools
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        register_tools(mcp)

        fn = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "datovka_search_box":
                fn = tool.fn
                break

        # Will fail at ISDS call but tests the routing logic
        with patch("mcp_datovka.tools.datovka.isds") as mock_isds:
            mock_isds.search_box.return_value = [{"box_id": "abc1234", "firm_name": "Test"}]
            result = json.loads(fn(query="04004621"))
            assert result[0]["box_id"] == "abc1234"
