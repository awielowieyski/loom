"""Shared utilities for LLM-based services."""

from __future__ import annotations


def strip_code_fences(text: str) -> str:
    """Strip markdown code fences from LLM response if present."""
    stripped = text.strip()
    if stripped.startswith("```"):
        # Remove opening fence (```json or ```)
        first_newline = stripped.index("\n")
        stripped = stripped[first_newline + 1 :]
    if stripped.endswith("```"):
        stripped = stripped[:-3]
    return stripped.strip()
