"""Phase 2: Content isolation — decompose a Skill into isolated fragments for evaluation."""

import re
import unicodedata
from typing import Any

from loom.models.eval import (
    CodeBlock,
    IsolatedFragments,
    StructuralReport,
)
from loom.models.skill import Skill

# Zero-width characters to strip
_ZERO_WIDTH = re.compile("[\u200b\u200c\u200d\ufeff]")

# RTL/LTR override characters to strip (U+202A-202E, U+2066-2069)
_RTL_OVERRIDES = re.compile("[\u202a-\u202e\u2066-\u2069]")

# Markdown heading pattern
_HEADING_RE = re.compile(r"^#{1,6}\s+.+$", re.MULTILINE)

# Fenced code block pattern (``` with optional language tag)
_CODE_BLOCK_RE = re.compile(
    r"^```(\w*)\s*\n(.*?)^```\s*$",
    re.MULTILINE | re.DOTALL,
)


def normalise_content(text: str) -> str:
    """Apply Unicode NFC normalisation and strip zero-width / RTL override chars."""
    text = unicodedata.normalize("NFC", text)
    text = _ZERO_WIDTH.sub("", text)
    text = _RTL_OVERRIDES.sub("", text)
    return text


def _extract_headings(content: str) -> list[str]:
    """Extract heading lines from markdown content."""
    return _HEADING_RE.findall(content)


def _extract_code_blocks(content: str) -> list[CodeBlock]:
    """Extract fenced code blocks with language tag and line position."""
    blocks: list[CodeBlock] = []
    for match in _CODE_BLOCK_RE.finditer(content):
        language = match.group(1) or ""
        code = match.group(2)
        # Calculate 1-based line number of the opening fence
        line_start = content[: match.start()].count("\n") + 1
        blocks.append(CodeBlock(language=language, code=code, line_start=line_start))
    return blocks


def _build_metadata(skill: Skill) -> dict[str, Any]:
    """Extract metadata fields from a Skill."""
    return {
        "name": skill.name,
        "description": skill.description,
        "tags": skill.tags,
        "cost_profile": str(skill.cost_profile),
        "estimated_duration": skill.estimated_duration,
        "scope": str(skill.scope),
        "dependency_count": len(skill.dependencies.mcp_servers) + len(skill.dependencies.apis),
    }


def isolate(skill: Skill, report: StructuralReport) -> IsolatedFragments:
    """Decompose a Skill into isolated fragments for Phase 3 evaluation.

    Args:
        skill: The skill to decompose.
        report: The Phase 1 structural report (provides content_hash and
                injection_indicators).

    Returns:
        IsolatedFragments with all extracted data.
    """
    normalised = normalise_content(skill.content)

    return IsolatedFragments(
        content_hash=report.content_hash,
        metadata=_build_metadata(skill),
        step_outline=_extract_headings(normalised),
        full_body=normalised,
        code_blocks=_extract_code_blocks(normalised),
        eval_scenarios=[s.model_dump() for s in skill.eval_spec.scenarios],
        injection_indicators=list(report.injection_indicators),
    )
