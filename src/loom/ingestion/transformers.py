"""Transform raw GitHub content into Loom SkillCreate models."""

from __future__ import annotations

import hashlib
import re
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

import yaml

from loom.models.skill import SkillCreate

if TYPE_CHECKING:
    from loom.ingestion.github_scraper import RawIngestionItem


def compute_content_hash(content: str) -> str:
    """SHA-256 hash of normalized content."""
    return hashlib.sha256(content.strip().encode("utf-8")).hexdigest()


def slugify(text: str, max_length: int = 80) -> str:
    """Convert text to a valid kebab-case slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    slug = slug[:max_length]
    return slug if slug else "unnamed"


def detect_format(content: str) -> str:
    """Detect if content has YAML frontmatter."""
    stripped = content.strip()
    if stripped.startswith("---"):
        # Check for closing ---
        end = stripped.find("---", 3)
        if end != -1:
            return "yaml_frontmatter"
    return "raw_markdown"


def parse_frontmatter(content: str) -> tuple[dict[str, object], str]:
    """Parse YAML frontmatter and return (metadata, body)."""
    stripped = content.strip()
    if not stripped.startswith("---"):
        return {}, content

    match = re.search(r"\n---\s*\n", stripped[3:])
    if match is None:
        return {}, content
    end = match.start() + 3  # offset from stripped[3:]
    frontmatter_text = stripped[3 : 3 + end].strip()
    body = stripped[3 + end + match.end() - match.start() :].strip()

    try:
        metadata = yaml.safe_load(frontmatter_text) or {}
    except yaml.YAMLError:
        metadata = {}

    return metadata, body


def extract_title_from_markdown(content: str, filename: str) -> str:
    """Extract first H1 heading, or derive from filename."""
    match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    # Derive from filename
    stem = PurePosixPath(filename).stem
    return stem.replace("-", " ").replace("_", " ").title()


def infer_category_from_path(file_path: str, default: str) -> str:
    """Infer a category from the file's directory structure."""
    parts = PurePosixPath(file_path).parts
    # Skip common root dirs like "rules/", "src/data/rules/"
    meaningful = [p for p in parts[:-1] if p not in ("rules", "src", "data", "prompts", "skills")]
    if meaningful:
        return f"ai-instructions/{slugify(meaningful[-1])}"
    return default


def extract_description(content: str, max_length: int = 200) -> str:
    """Extract a short description from content."""
    # Remove H1 heading
    body = re.sub(r"^#\s+.+$", "", content, count=1, flags=re.MULTILINE).strip()
    # Take first non-empty paragraph
    for paragraph in body.split("\n\n"):
        text = paragraph.strip()
        if text and not text.startswith("#") and not text.startswith("```"):
            cleaned = re.sub(r"\s+", " ", text)
            return cleaned[:max_length]
    return content[:max_length].replace("\n", " ").strip()


def _extract_openclaw_slug(file_path: str) -> str:
    """Extract skill slug from openclaw path like 'skills/author/skill-name/SKILL.md'."""
    parts = PurePosixPath(file_path).parts
    # Expected: ('skills', 'author', 'skill-name', 'SKILL.md')
    if len(parts) >= 4:
        return slugify(parts[2])  # the skill-name directory
    return slugify(PurePosixPath(file_path).stem)


def transform_to_skill_create(item: RawIngestionItem) -> SkillCreate:
    """Transform a raw ingestion item into a SkillCreate model."""
    fmt = detect_format(item.raw_content)

    if fmt == "yaml_frontmatter":
        frontmatter, body = parse_frontmatter(item.raw_content)
        name = str(frontmatter.get("name", frontmatter.get("title", "")))
        if not name:
            name = extract_title_from_markdown(body, item.file_path)
        description = str(frontmatter.get("description", extract_description(body)))
        raw_tags = frontmatter.get("tags", [item.source_type])
        if isinstance(raw_tags, str):
            tags: list[str] = [t.strip() for t in raw_tags.split(",")]
        elif isinstance(raw_tags, list):
            tags = [str(t) for t in raw_tags]
        else:
            tags = [item.source_type]
        content = body if body else item.raw_content
    else:
        name = extract_title_from_markdown(item.raw_content, item.file_path)
        description = extract_description(item.raw_content)
        tags = [item.source_type]
        content = item.raw_content

    # Slug: for openclaw, use the directory name; otherwise repo-stem
    if item.source_type == "openclaw":
        slug_base = _extract_openclaw_slug(item.file_path)
    else:
        stem = PurePosixPath(item.file_path).stem
        slug_base = slugify(f"{item.repo_name}-{stem}")

    # Version: prefer _meta.json, fall back to "1.0.0"
    version = "1.0.0"
    if item.meta_json:
        latest = item.meta_json.get("latest", {})
        if isinstance(latest, dict) and latest.get("version"):
            version = str(latest["version"])

    category = infer_category_from_path(item.file_path, "ai-instructions")

    return SkillCreate(
        slug=slug_base,
        name=name[:200],
        description=description[:500],
        content=content,
        category_slug=category,
        version=version,
        tags=tags[:10],
        source_uri=item.source_uri,
        license=item.detected_license,
    )
