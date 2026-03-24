"""Behavioral Judge — assesses Runner output with data-only protocol.

The Judge NEVER sees the original skill instructions. It evaluates only
the Runner's output against success criteria and quality dimensions.
This isolation prevents the Judge from being biased by the instructions.
"""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING, Any

from loom.models.behavioral import JudgeScore
from loom.services._llm_utils import strip_code_fences

if TYPE_CHECKING:
    from collections.abc import Callable

    from loom.models.behavioral import RunnerOutput
    from loom.models.common import EvalScenario, QualityDimension
    from loom.services.prompt_registry import PromptRegistry

logger = logging.getLogger(__name__)


class BehavioralJudge:
    """Assesses Runner output against success criteria. Never sees skill instructions."""

    def __init__(
        self,
        agent_factory: Callable[[str], Any],
        prompt_registry: PromptRegistry,
        model_id: str,
        max_retries: int = 2,
    ) -> None:
        self._agent_factory = agent_factory
        self._prompt_registry = prompt_registry
        self._model_id = model_id
        self._max_retries = max_retries

    async def judge(
        self,
        runner_output: RunnerOutput,
        scenario: EvalScenario,
        quality_dimensions: list[QualityDimension] | None = None,
    ) -> tuple[JudgeScore, int | None]:
        """Judge the Runner's output. Returns (score, latency_ms).

        SECURITY: The user message intentionally excludes skill_content.
        The judge only sees the runner's output and the success criteria.
        """
        variant = self._prompt_registry.get_behavioral_variant("judge")
        agent = self._agent_factory(variant.system_prompt)

        user_message = json.dumps(
            {
                "runner_output": runner_output.model_dump(),
                "success_criteria": scenario.success_criteria,
                "quality_dimensions": (
                    [d.model_dump() for d in quality_dimensions] if quality_dimensions else []
                ),
            }
        )

        attempts = 0
        last_error: Exception | None = None
        start_ns = time.monotonic_ns()

        while attempts <= self._max_retries:
            try:
                result = await agent.run(user_message)
                raw_text = result.output if hasattr(result, "output") else str(result)
                cleaned = strip_code_fences(raw_text)
                data = json.loads(cleaned)
                judge_score = JudgeScore(**data)
                elapsed_ms = (time.monotonic_ns() - start_ns) // 1_000_000
                return judge_score, int(elapsed_ms)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                attempts += 1
                logger.warning(
                    "Judge parse failure (attempt %d/%d): %s",
                    attempts,
                    self._max_retries + 1,
                    exc,
                )

        elapsed_ms = (time.monotonic_ns() - start_ns) // 1_000_000
        logger.error(
            "All %d judge attempts failed, returning fallback. Last error: %s",
            self._max_retries + 1,
            last_error,
        )
        fallback = JudgeScore(
            outcome_quality=0.0,
            completeness=0.0,
            efficiency=0.0,
            evidence="Judge response could not be parsed after retries",
            confidence=0.0,
            injection_detected=False,
        )
        return fallback, int(elapsed_ms)
