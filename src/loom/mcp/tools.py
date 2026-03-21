"""MCP tool definitions for Loom."""

from dataclasses import dataclass


@dataclass
class ToolDef:
    name: str
    description: str


def build_tools() -> list[ToolDef]:
    """Return the list of MCP tools exposed by Loom."""
    return [
        ToolDef(
            name="resolve",
            description="Resolve the best skill for a natural-language task description.",
        ),
        ToolDef(
            name="get_skill",
            description="Retrieve a skill by slug and optional version.",
        ),
        ToolDef(
            name="search",
            description="Search skills by query with optional filters.",
        ),
        ToolDef(
            name="list_categories",
            description="List all skill categories.",
        ),
    ]
