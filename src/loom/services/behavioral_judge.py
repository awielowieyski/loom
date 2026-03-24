"""Behavioral Judge — assesses Runner output with data-only protocol.

The Judge NEVER sees the original skill instructions. It evaluates only
the Runner's output against success criteria and quality dimensions.
This isolation prevents the Judge from being biased by the instructions.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from loom.models.behavioral import JudgeScore
from loom.services._llm_utils import llm_call_with_retry, strip_code_fences

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

    @property
    def model_id(self) -> str:
        return self._model_id

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

        def _parse(raw_text: str) -> JudgeScore:
            cleaned = strip_code_fences(raw_text)
            data = json.loads(cleaned)
            return JudgeScore(**data)

        result, elapsed_ms = await llm_call_with_retry(
            agent, user_message, _parse, self._max_retries, "Judge"
        )
        if result is None:
            fallback = JudgeScore(
                outcome_quality=0.0,
                completeness=0.0,
                efficiency=0.0,
                evidence="Judge response could not be parsed after retries",
                confidence=0.0,
                injection_detected=False,
            )
            return fallback, elapsed_ms
        return result, elapsed_ms
