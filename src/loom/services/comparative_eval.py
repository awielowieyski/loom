"""Comparative evaluation service — blind head-to-head skill comparison.

Two skills are run against the same scenarios through the Runner, then a
Comparative Judge scores both outputs blindly.  Assignment of skill to
"Output X" vs "Output Y" is randomised per scenario to eliminate position bias.
"""

from __future__ import annotations

import json
import logging
import random
from typing import TYPE_CHECKING, Any

from loom.models.behavioral import (
    ComparativeAxisScores,
    ComparativeResult,
    ComparisonSummary,
)
from loom.services._llm_utils import strip_code_fences

if TYPE_CHECKING:
    from collections.abc import Callable

    from loom.db.repositories.behavioral_eval_repo import BehavioralEvalRepo
    from loom.models.common import EvalScenario
    from loom.models.skill import Skill
    from loom.services.behavioral_runner import BehavioralRunner
    from loom.services.prompt_registry import PromptRegistry

logger = logging.getLogger(__name__)


class ComparativeEvalService:
    """Blind head-to-head comparison of two skills on the same scenarios."""

    def __init__(
        self,
        runner: BehavioralRunner,
        prompt_registry: PromptRegistry,
        agent_factory: Callable[[str], Any],
        model_id: str,
        behavioral_eval_repo: BehavioralEvalRepo,
        confidence_threshold: float = 0.60,
    ) -> None:
        self._runner = runner
        self._prompt_registry = prompt_registry
        self._agent_factory = agent_factory
        self._model_id = model_id
        self._repo = behavioral_eval_repo
        self._confidence_threshold = confidence_threshold

    async def compare(
        self,
        skill_a: Skill,
        skill_b: Skill,
        scenarios: list[EvalScenario],
    ) -> ComparisonSummary:
        """Run head-to-head comparison.  Returns per-scenario results and overall winner."""
        results: list[ComparativeResult] = []

        for scenario_idx, scenario in enumerate(scenarios):
            result = await self._compare_scenario(skill_a, skill_b, scenario, scenario_idx)
            results.append(result)

        # Determine overall winner by majority
        win_a = sum(1 for r in results if r.winner == "a")
        win_b = sum(1 for r in results if r.winner == "b")
        tie = sum(1 for r in results if r.winner == "tie")

        if win_a > win_b:
            overall = "a"
        elif win_b > win_a:
            overall = "b"
        else:
            overall = "tie"

        return ComparisonSummary(
            skill_a_id=skill_a.id,
            skill_b_id=skill_b.id,
            per_scenario=results,
            overall_winner=overall,
            win_count_a=win_a,
            win_count_b=win_b,
            tie_count=tie,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _compare_scenario(
        self,
        skill_a: Skill,
        skill_b: Skill,
        scenario: EvalScenario,
        scenario_index: int,
    ) -> ComparativeResult:
        """Compare two skills on a single scenario with blind assignment."""
        # 1. Randomise assignment to X / Y
        a_is_x = random.choice([True, False])  # noqa: S311

        if a_is_x:
            skill_x, skill_y = skill_a, skill_b
        else:
            skill_x, skill_y = skill_b, skill_a

        # 2. Run both skills through the Runner
        output_x, _ = await self._runner.run(skill_x.content, scenario)
        output_y, _ = await self._runner.run(skill_y.content, scenario)

        # 3. Build comparative judge message
        quality_dims = [d.model_dump() for d in (skill_a.eval_spec.quality_dimensions or [])]
        user_message = json.dumps(
            {
                "output_x": output_x.model_dump(),
                "output_y": output_y.model_dump(),
                "success_criteria": scenario.success_criteria,
                "quality_dimensions": quality_dims,
            }
        )

        # 4. Get system prompt and call judge (with retry on JSON parse failure)
        variant = self._prompt_registry.get_behavioral_variant("comparative_judge")
        agent = self._agent_factory(variant.system_prompt)

        data: dict[str, Any] | None = None
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                raw_result = await agent.run(user_message)
                raw_text = raw_result.output if hasattr(raw_result, "output") else str(raw_result)
                cleaned = strip_code_fences(raw_text)
                data = json.loads(cleaned)
                break
            except (json.JSONDecodeError, ValueError, KeyError) as exc:
                last_error = exc
                logger.warning(
                    "Comparative judge JSON parse failed (attempt %d/3) for scenario %d: %s",
                    attempt + 1,
                    scenario_index,
                    exc,
                )

        if data is None:
            logger.error(
                "Comparative judge failed after 3 attempts for scenario %d, returning tie: %s",
                scenario_index,
                last_error,
            )
            data = {
                "score_x": {},
                "score_y": {},
                "confidence": 0.0,
                "reasoning": f"Judge parse failure after 3 attempts: {last_error}",
                "preference": "TIE",
            }

        # 5. Parse scores
        score_x = ComparativeAxisScores(**(data.get("score_x", {})))
        score_y = ComparativeAxisScores(**(data.get("score_y", {})))
        confidence = float(data.get("confidence", 0.0))
        reasoning = str(data.get("reasoning", ""))
        raw_preference = str(data.get("preference", "tie")).upper()

        # 6. Apply confidence threshold
        if confidence < self._confidence_threshold:
            raw_preference = "TIE"

        # 7. Map X/Y preference back to a/b
        if raw_preference == "X":
            winner = "a" if a_is_x else "b"
        elif raw_preference == "Y":
            winner = "b" if a_is_x else "a"
        else:
            winner = "tie"

        # Map scores back to a/b order
        if a_is_x:
            score_a, score_b = score_x, score_y
        else:
            score_a, score_b = score_y, score_x

        # 8. Persist
        comparative_result = await self._repo.create_comparative_result(
            skill_a_id=skill_a.id,
            skill_a_version=skill_a.version,
            skill_b_id=skill_b.id,
            skill_b_version=skill_b.version,
            scenario_index=scenario_index,
            winner=winner,
            score_a=score_a.model_dump(),
            score_b=score_b.model_dump(),
            preference_confidence=confidence,
            reasoning=reasoning,
            judge_model_id=self._model_id,
        )

        return comparative_result
