"""Amendment triage pipeline — classifies amendments via semantic diff + behavioral diff.

Combines embedding similarity (semantic) with head-to-head comparative evaluation
(behavioral) to classify an amendment as refinement, regression, variant, extension,
or rejected.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from loom.models.common import AmendmentClassification
from loom.services.duplicate_detector import cosine_similarity

if TYPE_CHECKING:
    from loom.models.behavioral import AmendmentTriageResult, ComparisonSummary
    from loom.models.common import EvalScenario
    from loom.models.skill import Skill
    from loom.services.comparative_eval import ComparativeEvalService

logger = logging.getLogger(__name__)

# Safety floor: any per-scenario safety score below this triggers rejection
_SAFETY_FLOOR = 0.30


class AmendmentTriagePipeline:
    """Classifies amendments via semantic diff + behavioral diff."""

    def __init__(
        self,
        embedder: Any,
        comparative_eval: ComparativeEvalService,
        semantic_threshold_high: float = 0.95,
        semantic_threshold_low: float = 0.70,
    ) -> None:
        self._embedder = embedder
        self._comparative_eval = comparative_eval
        self._threshold_high = semantic_threshold_high
        self._threshold_low = semantic_threshold_low

    async def triage(
        self,
        old_skill: Skill,
        new_skill: Skill,
        scenarios: list[EvalScenario],
    ) -> AmendmentTriageResult:
        """Classify an amendment.  Returns classification + evidence."""
        from loom.models.behavioral import AmendmentTriageResult as TriageResult

        # 1. Semantic diff: embed both skills' content, compute cosine similarity
        old_embedding = await self._embedder.embed(old_skill.content)
        new_embedding = await self._embedder.embed(new_skill.content)
        similarity = cosine_similarity(old_embedding, new_embedding)

        # 2. Behavioral diff: run comparative eval on old_skill's eval scenarios
        comparison: ComparisonSummary | None = None
        if scenarios:
            comparison = await self._comparative_eval.compare(old_skill, new_skill, scenarios)

        # 3. Classify based on the matrix
        classification = self._classify(similarity, comparison)

        evidence = (
            f"Semantic similarity: {similarity:.3f}. "
            f"Comparison: {self._comparison_summary_text(comparison)}."
        )

        return TriageResult(
            classification=classification,
            semantic_similarity=similarity,
            comparison=comparison,
            evidence=evidence,
        )

    # ------------------------------------------------------------------
    # Classification matrix
    # ------------------------------------------------------------------

    def _classify(
        self,
        similarity: float,
        comparison: ComparisonSummary | None,
    ) -> AmendmentClassification:
        """Apply the classification matrix from spec Section 3.2."""
        # Check safety first: any per-scenario safety failure -> rejected
        if comparison is not None:
            for result in comparison.per_scenario:
                # Check if new skill (b) has a safety failure
                if result.score_b.safety < _SAFETY_FLOOR:
                    return AmendmentClassification.REJECTED

        new_is_better_or_equal = self._new_at_least_as_good(comparison)

        if similarity < self._threshold_low:
            # Low similarity -> extension (regardless of behavioral)
            return AmendmentClassification.EXTENSION

        if similarity >= self._threshold_high:
            # High similarity
            if new_is_better_or_equal:
                return AmendmentClassification.REFINEMENT
            return AmendmentClassification.REGRESSION

        # Medium similarity (between low and high thresholds)
        if new_is_better_or_equal:
            return AmendmentClassification.REFINEMENT
        return AmendmentClassification.VARIANT

    @staticmethod
    def _new_at_least_as_good(comparison: ComparisonSummary | None) -> bool:
        """Determine if new skill (b) is at least as good as old (a).

        True when b wins or ties the majority of scenarios.
        """
        if comparison is None:
            # No scenarios to compare -> assume no regression
            return True

        # Count scenarios where new (b) is preferred or tied
        b_ok = sum(1 for r in comparison.per_scenario if r.winner in ("b", "tie"))
        return b_ok >= len(comparison.per_scenario) / 2

    @staticmethod
    def _comparison_summary_text(comparison: ComparisonSummary | None) -> str:
        if comparison is None:
            return "no scenarios evaluated"
        return (
            f"A wins {comparison.win_count_a}, "
            f"B wins {comparison.win_count_b}, "
            f"ties {comparison.tie_count}"
        )
