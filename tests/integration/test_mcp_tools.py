"""Tests for MCP tool definitions."""

from loom.mcp.tools import ToolDef, build_tools


def test_build_tools_returns_four_tools() -> None:
    """build_tools() should return exactly 4 ToolDef instances."""
    tools = build_tools()
    assert len(tools) == 4
    assert all(isinstance(t, ToolDef) for t in tools)


def test_build_tools_has_expected_names() -> None:
    """build_tools() should include resolve, get_skill, search, list_categories."""
    names = {t.name for t in build_tools()}
    assert names == {"resolve", "get_skill", "search", "list_categories"}
