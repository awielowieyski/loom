"""Shared utilities for LLM-based services."""

from __future__ import annotations

import logging
import time
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


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


async def llm_call_with_retry(
    agent: Any,
    message: str,
    parse_fn: Any,
    max_retries: int,
    label: str,
) -> tuple[T | None, int]:
    """Run an LLM agent call with retries and timing.

    Args:
        agent: The LLM agent (must have an async `run` method).
        message: The user message to send.
        parse_fn: Callable that takes raw text and returns a parsed result.
                  Should raise on parse failure to trigger retry.
        max_retries: Maximum number of retry attempts (0 = single attempt).
        label: Human-readable label for log messages (e.g. "Runner", "Judge").

    Returns:
        Tuple of (parsed_result_or_None, elapsed_ms). Returns None on failure.
    """
    attempts = 0
    last_error: Exception | None = None
    start_ns = time.monotonic_ns()

    while attempts <= max_retries:
        try:
            result = await agent.run(message)
            raw_text = result.output if hasattr(result, "output") else str(result)
            parsed = parse_fn(raw_text)
            elapsed_ms = (time.monotonic_ns() - start_ns) // 1_000_000
            return parsed, int(elapsed_ms)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            attempts += 1
            logger.warning(
                "%s parse failure (attempt %d/%d): %s",
                label,
                attempts,
                max_retries + 1,
                exc,
            )

    elapsed_ms = (time.monotonic_ns() - start_ns) // 1_000_000
    logger.error(
        "All %d %s attempts failed, returning fallback. Last error: %s",
        max_retries + 1,
        label,
        last_error,
    )
    return None, int(elapsed_ms)
