"""Behavioral Runner — simulates skill execution via a Runner LLM.

The Runner receives skill instructions and a scenario in a JSON user message
(data-only protocol). It simulates step-by-step execution and produces
structured output. It does NOT judge quality — that's the Judge's job.
"""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING, Any

from loom.models.behavioral import RunnerOutput
from loom.services._llm_utils import strip_code_fences

if TYPE_CHECKING:
    from collections.abc import Callable

    from loom.models.common import EvalScenario
    from loom.services.prompt_registry import PromptRegistry

logger = logging.getLogger(__name__)


class BehavioralRunner:
    """Simulates skill execution by sending instructions + scenario to a Runner LLM."""

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

    async def run(
        self,
        skill_content: str,
        scenario: EvalScenario,
    ) -> tuple[RunnerOutput, int | None]:
        """Run skill instructions against a scenario.

        Returns:
            Tuple of (RunnerOutput, latency_ms). On parse failure after retries,
            returns a fallback RunnerOutput with empty fields.
        """
        variant = self._prompt_registry.get_behavioral_variant("runner")
        agent = self._agent_factory(variant.system_prompt)

        user_message = json.dumps(
            {
                "instructions": skill_content,
                "scenario": {
                    "input_context": scenario.input_context,
                    "success_criteria": scenario.success_criteria,
                    "description": scenario.description,
                },
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
                runner_output = RunnerOutput(**data)
                elapsed_ms = (time.monotonic_ns() - start_ns) // 1_000_000
                return runner_output, int(elapsed_ms)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                attempts += 1
                logger.warning(
                    "Runner parse failure (attempt %d/%d): %s",
                    attempts,
                    self._max_retries + 1,
                    exc,
                )

        elapsed_ms = (time.monotonic_ns() - start_ns) // 1_000_000
        logger.error(
            "All %d runner attempts failed, returning fallback. Last error: %s",
            self._max_retries + 1,
            last_error,
        )
        return RunnerOutput(), int(elapsed_ms)
