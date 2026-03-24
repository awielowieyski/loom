"""Breaking change detection for capabilities affected by skill amendments.

When a skill used as a step in one or more capabilities is amended, this
detector runs comparative evaluation (old vs new) against each affected
capability's scenarios.  If the new skill degrades performance, a
BreakingChangeReport is produced.  For M4 this is advisory — it does not
block amendments.
"""

from __future__ import annotations

import logging
import statistics
from typing import TYPE_CHECKING, Any

from loom.models.behavioral import BreakingChangeReport

if TYPE_CHECKING:
    from loom.models.common import EvalScenario
    from loom.models.skill import Skill
    from loom.services.comparative_eval import ComparativeEvalService

logger = logging.getLogger(__name__)


class BreakingChangeDetector:
    """Detects breaking changes when a skill used in capabilities is amended."""

    def __init__(
        self,
        capability_repo: Any,
        comparative_eval: ComparativeEvalService,
    ) -> None:
        self._capability_repo = capability_repo
        self._comparative_eval = comparative_eval

    async def detect(
        self,
        amended_skill_slug: str,
        old_skill: Skill,
        new_skill: Skill,
    ) -> list[BreakingChangeReport]:
        """Check if amending this skill breaks any capabilities.

        Returns a list of BreakingChangeReport for each capability where the
        new skill performs worse than the old one.
        """
        # 1. Find capabilities that reference the amended skill
        affected = await self._find_affected_capabilities(amended_skill_slug)
        if not affected:
            return []

        reports: list[BreakingChangeReport] = []

        for capability in affected:
            # 2. Find which step(s) reference this skill
            step_indices = self._find_step_indices(capability, amended_skill_slug)

            # 3. Get the capability's eval scenarios
            scenarios: list[EvalScenario] = []
            if hasattr(capability, "eval_spec") and capability.eval_spec:
                scenarios = capability.eval_spec.scenarios or []

            if not scenarios:
                continue

            # 4. Run comparative eval: old skill vs new skill on capability scenarios
            comparison = await self._comparative_eval.compare(old_skill, new_skill, scenarios)

            # 5. Check if new is worse on any scenario
            degraded = [
                r.scenario_index
                for r in comparison.per_scenario
                if r.winner == "a"  # old skill won -> new is worse
            ]

            if degraded:
                # Compute approximate scores from axis scores
                old_scores = [
                    statistics.mean(
                        [
                            r.score_a.outcome_quality,
                            r.score_a.completeness,
                            r.score_a.efficiency,
                        ]
                    )
                    for r in comparison.per_scenario
                ]
                new_scores = [
                    statistics.mean(
                        [
                            r.score_b.outcome_quality,
                            r.score_b.completeness,
                            r.score_b.efficiency,
                        ]
                    )
                    for r in comparison.per_scenario
                ]
                old_mean = statistics.mean(old_scores)
                new_mean = statistics.mean(new_scores)

                for step_idx in step_indices:
                    reports.append(
                        BreakingChangeReport(
                            capability_slug=capability.slug,
                            capability_name=capability.name,
                            step_index=step_idx,
                            old_score=round(old_mean, 4),
                            new_score=round(new_mean, 4),
                            score_delta=round(new_mean - old_mean, 4),
                            degraded_scenarios=degraded,
                        )
                    )

        return reports

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _find_affected_capabilities(self, skill_slug: str) -> list[Any]:
        """Query capabilities that reference the given skill slug in their steps."""
        # Use the repo to search for capabilities whose steps reference this skill
        all_caps = await self._capability_repo.search_by_skill_ref(skill_slug)
        return list(all_caps)

    @staticmethod
    def _find_step_indices(capability: Any, skill_slug: str) -> list[int]:
        """Return step indices that reference the given skill slug."""
        indices = []
        target_refs = {f"loom://{skill_slug}", f"corp://{skill_slug}"}
        for i, step in enumerate(capability.steps):
            ref = step.skill_ref if hasattr(step, "skill_ref") else step.get("skill_ref", "")
            if ref in target_refs:
                indices.append(i)
        return indices
