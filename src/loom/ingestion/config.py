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
    # Anthropic's official skills repo — high quality, structured prompts
    RepoSource(
        owner="anthropics",
        repo="anthropic-cookbook",
        paths=["misc/prompt_caching/", "misc/prompt_engineering/", "tool_use/"],
        file_patterns=["*.md"],
        source_type="cookbook",
        default_category="ai-instructions",
        license_override="MIT",
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
