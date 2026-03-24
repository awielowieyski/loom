"""Shared utilities for LLM-based services."""

from __future__ import annotations


def strip_code_fences(text: str) -> str:
    """Strip markdown code fences from LLM response if present."""
    stripped = text.strip()
    if stripped.startswith("```"):
        # Remove opening fence (```json or ```)
        first_newline = stripped.find("\n")
        # Fence with no newline — just strip the opening marker
        stripped = stripped[3:] if first_newline == -1 else stripped[first_newline + 1 :]
    if stripped.endswith("```"):
        stripped = stripped[:-3]
    return stripped.strip()
