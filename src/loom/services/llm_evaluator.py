"""Phase 3: LLM-based dimension evaluation using the data-only protocol.

Each quality dimension (clarity, completeness, safety, correctness) is assessed
in an isolated LLM call. Skill data is passed as a JSON user message — never
interpolated into the system prompt. This is the data-only protocol.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from loom.models.common import EvalDimension
from loom.models.eval import DimensionResult, IsolatedFragments
from loom.services.prompt_registry import PromptRegistry

logger = logging.getLogger(__name__)

# Fragment-to-dimension mapping (dimension isolation)
# Each dimension only sees the fragments it needs.
_DIMENSION_FRAGMENT_MAP: dict[EvalDimension, list[str]] = {
    EvalDimension.CLARITY: ["step_outline"],
    EvalDimension.COMPLETENESS: ["metadata", "step_outline"],
    EvalDimension.SAFETY: ["full_body", "injection_indicators"],
    EvalDimension.CORRECTNESS: ["eval_scenarios", "code_blocks"],
}


def _extract_fragment(fragments: IsolatedFragments, dimension: EvalDimension) -> str:
    """Extract and JSON-encode the relevant fragment for a dimension."""
    keys = _DIMENSION_FRAGMENT_MAP[dimension]
    parts: dict[str, Any] = {}
    for key in keys:
        value = getattr(fragments, key)
        # Convert Pydantic models to dicts for JSON serialisation
        if isinstance(value, list) and value and hasattr(value[0], "model_dump"):
            parts[key] = [item.model_dump() for item in value]
        elif hasattr(value, "model_dump"):
            parts[key] = value.model_dump()
        else:
            parts[key] = value
    # Flatten to single string if only one key
    if len(parts) == 1:
        return json.dumps(next(iter(parts.values())))
    return json.dumps(parts)


def _build_user_message(
    fragments: IsolatedFragments,
    dimension: EvalDimension,
) -> str:
    """Build the JSON user message for the data-only protocol.

    The message contains only the skill fragment and the dimension name.
    Safety additionally includes injection_indicators.
    """
    fragment_str = _extract_fragment(fragments, dimension)
    msg: dict[str, Any] = {
        "skill_fragment": fragment_str,
        "dimension": dimension.value,
    }
    if dimension == EvalDimension.SAFETY:
        msg["injection_indicators"] = [
            ind.model_dump() for ind in fragments.injection_indicators
        ]
    return json.dumps(msg)


def _parse_response(raw: str, dimension: EvalDimension) -> DimensionResult:
    """Parse and validate an LLM response into a DimensionResult.

    Raises ``ValueError`` if the response cannot be parsed or validated.
    """
    data = json.loads(raw)

    score = float(data["score"])
    if not 0.0 <= score <= 1.0:
        msg = f"score {score} not in [0, 1]"
        raise ValueError(msg)

    evidence = data.get("evidence", [])
    if not isinstance(evidence, list):
        msg = "evidence must be a list"
        raise ValueError(msg)

    confidence = float(data.get("confidence", 0.0))
    if not 0.0 <= confidence <= 1.0:
        msg = f"confidence {confidence} not in [0, 1]"
        raise ValueError(msg)

    injection_detected = bool(data.get("injection_detected", False))
    injection_detail = data.get("injection_detail")

    return DimensionResult(
        dimension=dimension,
        score=score,
        evidence=evidence,
        injection_detected=injection_detected,
        injection_detail=injection_detail,
        confidence=confidence,
    )


def _fallback_result(dimension: EvalDimension) -> DimensionResult:
    """Return a low-confidence fallback result after parse failures."""
    return DimensionResult(
        dimension=dimension,
        score=0.0,
        evidence=["LLM response could not be parsed after retries"],
        injection_detected=False,
        injection_detail=None,
        confidence=0.0,
    )


class LLMEvaluator:
    """Isolated LLM evaluator using the data-only protocol.

    Each dimension is assessed in a separate LLM call with its own
    system prompt (from the prompt registry) and only the relevant
    skill fragments.
    """

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

    async def evaluate_dimension(
        self,
        fragments: IsolatedFragments,
        dimension: EvalDimension,
    ) -> DimensionResult:
        """Evaluate a single dimension using the data-only protocol."""
        variant = self._prompt_registry.get_variant(dimension)
        agent = self._agent_factory(variant.system_prompt)
        user_message = _build_user_message(fragments, dimension)

        attempts = 0
        last_error: Exception | None = None

        while attempts <= self._max_retries:
            try:
                result = await agent.run(user_message)
                # pydantic-ai Agent.run returns a RunResult; extract text
                raw_text = result.output if hasattr(result, "output") else str(result)
                return _parse_response(raw_text, dimension)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                attempts += 1
                logger.warning(
                    "LLM eval parse failure (attempt %d/%d) for %s: %s",
                    attempts,
                    self._max_retries + 1,
                    dimension.value,
                    exc,
                )

        logger.error(
            "All %d attempts failed for %s, returning fallback. Last error: %s",
            self._max_retries + 1,
            dimension.value,
            last_error,
        )
        return _fallback_result(dimension)

    async def evaluate_all(
        self,
        fragments: IsolatedFragments,
        n_runs: int = 3,
    ) -> dict[str, list[DimensionResult]]:
        """Evaluate all dimensions, running each *n_runs* times.

        Returns a dict mapping dimension name to a list of DimensionResults.
        """
        results: dict[str, list[DimensionResult]] = {}
        for dimension in EvalDimension:
            dim_results: list[DimensionResult] = []
            for _ in range(n_runs):
                result = await self.evaluate_dimension(fragments, dimension)
                dim_results.append(result)
            results[dimension.value] = dim_results
        return results
