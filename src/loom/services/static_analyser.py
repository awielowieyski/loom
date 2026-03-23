"""StaticAnalyser: Phase 1 deterministic validation of skill structure."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import TYPE_CHECKING

from loom.models.eval import InjectionIndicator, StructuralReport

if TYPE_CHECKING:
    from loom.models.common import EvalSpec
    from loom.models.skill import SkillCreate

MIN_CONTENT_LENGTH = 10
MAX_CONTENT_LENGTH = 50_000
MAX_SCENARIOS = 20
MAX_DEPENDENCIES = 15
MAX_STEPS = 50
NESTING_WARN = 4
NESTING_REJECT = 6

# Regex catalogue for injection pattern scanning.
INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "ignore_instructions",
        re.compile(
            r"ignore\s+(previous|above|all)\s+(instructions?|prompts?|rules?)",
            re.IGNORECASE,
        ),
    ),
    ("role_assignment", re.compile(r"(system|assistant|user)\s*:", re.IGNORECASE)),
    ("special_tokens", re.compile(r"<\|im_(start|end)\|>")),
    ("role_tags", re.compile(r"<\|(system|user|assistant)\|>")),
    ("identity_override", re.compile(r"you\s+are\s+(now|a|an)\s+", re.IGNORECASE)),
    ("new_instructions", re.compile(r"(new|updated|real)\s+instructions?\s*:", re.IGNORECASE)),
    ("forget_instructions", re.compile(r"forget\s+(everything|all|previous)", re.IGNORECASE)),
    ("important_override", re.compile(r"IMPORTANT:\s*(ignore|override|disregard)", re.IGNORECASE)),
    ("prompt_tags", re.compile(r"</?(system|instruction|prompt)>", re.IGNORECASE)),
]

# Zero-width and RTL override characters to strip during normalisation.
_ZERO_WIDTH_RE = re.compile(
    "[\u200b\u200c\u200d\ufeff"  # zero-width space/joiner/non-joiner/BOM
    "\u200e\u200f"  # LTR/RTL marks
    "\u202a\u202b\u202c\u202d\u202e"  # LTR/RTL embedding/override/pop
    "\u2066\u2067\u2068\u2069"  # LTR/RTL/FSI isolates and pop
    "]"
)

_HEADING_RE = re.compile(r"^(#{1,6})\s+", re.MULTILINE)


def _normalise_content(content: str) -> str:
    """NFC normalise, strip zero-width chars and RTL overrides."""
    text = unicodedata.normalize("NFC", content)
    return _ZERO_WIDTH_RE.sub("", text)


def _content_hash(normalised: str) -> str:
    """SHA-256 hash of normalised content, prefixed with 'sha256:'."""
    digest = hashlib.sha256(normalised.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _count_steps(content: str) -> int:
    """Count markdown headings as step indicators."""
    return len(_HEADING_RE.findall(content))


def _max_nesting_depth(content: str) -> int:
    """Return the maximum heading nesting depth found."""
    matches = _HEADING_RE.findall(content)
    if not matches:
        return 0
    return max(len(m) for m in matches)


def _scan_injections(content: str) -> list[InjectionIndicator]:
    """Scan content for injection patterns, returning indicators."""
    indicators: list[InjectionIndicator] = []
    lines = content.split("\n")
    for line_num, line in enumerate(lines, start=1):
        for pattern_name, pattern_re in INJECTION_PATTERNS:
            match = pattern_re.search(line)
            if match:
                indicators.append(
                    InjectionIndicator(
                        line=line_num,
                        pattern=pattern_name,
                        matched_text=match.group(),
                    )
                )
    return indicators


def _complexity_score(
    content: str,
    dep_count: int,
    step_count: int,
) -> float:
    """Compute a weighted complexity score in 0-1 range.

    Weights: tokens 40%, deps 30%, steps 30%.
    Each component is normalised against its maximum before weighting.
    """
    # Token estimate: split on whitespace.
    token_count = len(content.split())
    # Normalise each component to 0-1.
    # Use reasonable upper bounds for normalisation.
    token_norm = min(token_count / 10_000, 1.0)
    dep_norm = min(dep_count / MAX_DEPENDENCIES, 1.0)
    step_norm = min(step_count / MAX_STEPS, 1.0)

    score = 0.4 * token_norm + 0.3 * dep_norm + 0.3 * step_norm
    return min(max(score, 0.0), 1.0)


class StaticAnalyser:
    """Phase 1: deterministic structural validation of skills.

    Pure functions, no external dependencies, no async.
    """

    def analyse(self, skill: SkillCreate) -> StructuralReport:
        """Run all static checks and return a StructuralReport."""
        errors: list[str] = []
        warnings: list[str] = []

        # --- Content length bounds ---
        if not skill.content or len(skill.content) < MIN_CONTENT_LENGTH:
            errors.append(f"Skill content must be at least {MIN_CONTENT_LENGTH} characters long")
        if skill.content and len(skill.content) > MAX_CONTENT_LENGTH:
            errors.append(
                f"Skill content exceeds maximum length of {MAX_CONTENT_LENGTH} characters"
            )

        # --- Eval spec validation ---
        eval_spec: EvalSpec = skill.eval_spec
        if not eval_spec.scenarios:
            errors.append("Skill eval_spec must contain at least 1 scenario")
        elif len(eval_spec.scenarios) > MAX_SCENARIOS:
            errors.append(f"Skill eval_spec must contain at most {MAX_SCENARIOS} scenarios")

        # --- Dependency count ---
        dep_count = len(skill.dependencies.mcp_servers) + len(skill.dependencies.apis)
        if dep_count > MAX_DEPENDENCIES:
            errors.append(f"Total dependencies ({dep_count}) exceeds maximum of {MAX_DEPENDENCIES}")

        # --- MCP URI validation ---
        for dep in skill.dependencies.mcp_servers:
            if not dep.uri:
                errors.append("MCP server dependency has empty URI")

        # --- Content-dependent checks (only if content exists) ---
        normalised = ""
        injection_indicators: list[InjectionIndicator] = []
        step_count = 0
        nesting = 0

        if skill.content:
            normalised = _normalise_content(skill.content)

            # Step count
            step_count = _count_steps(normalised)
            if step_count > MAX_STEPS:
                errors.append(f"Step count ({step_count}) exceeds maximum of {MAX_STEPS}")

            # Nesting depth
            nesting = _max_nesting_depth(normalised)
            if nesting > NESTING_REJECT:
                errors.append(
                    f"Heading nesting depth ({nesting}) exceeds maximum of {NESTING_REJECT}"
                )
            elif nesting > NESTING_WARN:
                warnings.append(
                    f"Heading nesting depth ({nesting}) exceeds recommended"
                    f" maximum of {NESTING_WARN}"
                )

            # Injection scanning — indicators populated, NOT causing rejection.
            injection_indicators = _scan_injections(normalised)

        # --- Complexity score ---
        score = _complexity_score(normalised, dep_count, step_count)

        # --- Content hash ---
        content_hash = _content_hash(normalised) if normalised else ""

        return StructuralReport(
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            injection_indicators=injection_indicators,
            complexity_score=score,
            content_hash=content_hash,
        )
