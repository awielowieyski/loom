"""Ingestion source configuration."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RepoSource:
    """A GitHub repository to scrape for skills."""

    owner: str
    repo: str
    paths: list[str] = field(default_factory=lambda: [""])
    file_patterns: list[str] = field(default_factory=lambda: ["*.md"])
    source_type: str = "markdown"
    default_category: str = "ai-instructions"
    license_override: str | None = None


DEFAULT_REPOS: list[RepoSource] = [
    # OpenClaw skills archive — structured SKILL.md + _meta.json format
    RepoSource(
        owner="openclaw",
        repo="skills",
        paths=["skills/"],
        file_patterns=["SKILL.md"],
        source_type="openclaw",
        default_category="ai-instructions",
    ),
]

# Extended repos for bulk ingestion (use --repo flag to target specific ones)
EXTENDED_REPOS: list[RepoSource] = [
    *DEFAULT_REPOS,
    RepoSource(
        owner="PatrickJS",
        repo="awesome-cursorrules",
        paths=["rules/"],
        file_patterns=["*.md", "*.mdc"],
        source_type="cursor-rules",
        default_category="ai-instructions",
    ),
    RepoSource(
        owner="pontusab",
        repo="cursor.directory",
        paths=["src/data/rules/"],
        file_patterns=["*.md", "*.mdc"],
        source_type="cursor-rules",
        default_category="ai-instructions",
    ),
]
