"""Behavioral Runner — simulates skill execution via a Runner LLM.

The Runner receives skill instructions and a scenario in a JSON user message
(data-only protocol). It simulates step-by-step execution and produces
structured output. It does NOT judge quality — that's the Judge's job.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from loom.models.behavioral import RunnerOutput
from loom.services._llm_utils import llm_call_with_retry, strip_code_fences

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

    @property
    def model_id(self) -> str:
        return self._model_id

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

        def _parse(raw_text: str) -> RunnerOutput:
            cleaned = strip_code_fences(raw_text)
            data = json.loads(cleaned)
            return RunnerOutput(**data)

        result, elapsed_ms = await llm_call_with_retry(
            agent, user_message, _parse, self._max_retries, "Runner"
        )
        if result is None:
            return RunnerOutput(), elapsed_ms
        return result, elapsed_ms
