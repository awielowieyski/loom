"""Phase 5: Score aggregation — combine dimension results into a final EvalResult."""

from __future__ import annotations

import statistics

from loom.models.common import EvalDimension
from loom.models.eval import DimensionResult, EvalResult, SandboxResult, StructuralReport

EVALUATOR_VERSION = "m2-v0.1.0"

DIMENSION_WEIGHTS: dict[str, float] = {
    "clarity": 0.25,
    "completeness": 0.30,
    "safety": 0.25,
    "correctness": 0.20,
}

PASS_THRESHOLD = 0.50


class ScoreAggregator:
    """Aggregate per-dimension LLM evaluation runs into a final EvalResult.

    Pure function service — no async, no external dependencies.
    Uses median consensus for outlier resistance.
    """

    def __init__(self, *, pass_threshold: float = PASS_THRESHOLD) -> None:
        self._pass_threshold = pass_threshold

    def aggregate(
        self,
        structural: StructuralReport,
        dimensions: dict[EvalDimension, list[DimensionResult]],
        sandbox: SandboxResult | None = None,
    ) -> EvalResult:
        """Aggregate all phase results into a single EvalResult.

        Args:
            structural: Phase 1 structural report.
            dimensions: Phase 3 per-dimension results (multiple runs each).
            sandbox: Phase 4 sandbox result (None if sandbox not run).

        Returns:
            Final EvalResult with composite score and pass/fail verdict.
        """
        # Gate 1: structural failure short-circuits everything.
        if not structural.passed:
            return EvalResult(
                passed=False,
                composite_score=0.0,
                content_hash=structural.content_hash,
                evaluator_version=EVALUATOR_VERSION,
            )

        # Per-dimension median scores.
        dimension_scores: dict[str, float] = {}
        dimension_confidence: dict[str, float] = {}
        injection_flagged = False

        for dim in EvalDimension:
            runs = dimensions.get(dim, [])
            if not runs:
                dimension_scores[dim.value] = 0.0
                dimension_confidence[dim.value] = 0.0
                continue

            scores = [r.score for r in runs]
            dimension_scores[dim.value] = statistics.median(scores)

            # Confidence: 1.0 - spread (max - min).
            spread = max(scores) - min(scores)
            dimension_confidence[dim.value] = 1.0 - spread

            # Injection detection: any run on any dimension.
            if any(r.injection_detected for r in runs):
                injection_flagged = True

        # Composite: weighted average of dimension medians.
        composite = sum(
            DIMENSION_WEIGHTS[dim] * dimension_scores.get(dim, 0.0) for dim in DIMENSION_WEIGHTS
        )

        # Overall confidence: min across dimensions.
        confidence_values = list(dimension_confidence.values())
        overall_confidence = min(confidence_values) if confidence_values else 0.0

        # Sandbox gate.
        sandbox_passed: bool | None = None
        if sandbox is not None:
            sandbox_passed = sandbox.passed

        # Pass decision: composite >= threshold AND sandbox not failed AND no injection.
        passed = composite >= self._pass_threshold and not injection_flagged
        if sandbox is not None and not sandbox.passed:
            passed = False

        return EvalResult(
            passed=passed,
            composite_score=composite,
            dimension_scores=dimension_scores,
            dimension_confidence=dimension_confidence,
            overall_confidence=overall_confidence,
            injection_flagged=injection_flagged,
            sandbox_passed=sandbox_passed,
            content_hash=structural.content_hash,
            evaluator_version=EVALUATOR_VERSION,
        )
