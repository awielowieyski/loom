"""Tests for ScoreAggregator Phase 5 score aggregation."""

import pytest

from loom.models.common import EvalDimension
from loom.models.eval import DimensionResult, SandboxResult, StructuralReport
from loom.services.score_aggregator import (
    DIMENSION_WEIGHTS,
    EVALUATOR_VERSION,
    PASS_THRESHOLD,
    ScoreAggregator,
)


@pytest.fixture
def aggregator() -> ScoreAggregator:
    return ScoreAggregator()


def _passing_structural(content_hash: str = "sha256:abc123") -> StructuralReport:
    return StructuralReport(passed=True, content_hash=content_hash)


def _failing_structural() -> StructuralReport:
    return StructuralReport(passed=False, errors=["content too short"], content_hash="sha256:bad")


def _dim_result(
    dimension: EvalDimension,
    score: float,
    confidence: float = 1.0,
    injection_detected: bool = False,
    injection_detail: str | None = None,
) -> DimensionResult:
    return DimensionResult(
        dimension=dimension,
        score=score,
        evidence=["test evidence"],
        injection_detected=injection_detected,
        injection_detail=injection_detail,
        confidence=confidence,
    )


def _uniform_dimensions(
    score: float,
    runs_per_dim: int = 3,
) -> dict[EvalDimension, list[DimensionResult]]:
    """Create uniform scores across all dimensions."""
    return {dim: [_dim_result(dim, score) for _ in range(runs_per_dim)] for dim in EvalDimension}


# --- Structural failure overrides all ---


def test_structural_failure_overrides_all(aggregator: ScoreAggregator) -> None:
    result = aggregator.aggregate(
        structural=_failing_structural(),
        dimensions=_uniform_dimensions(0.9),
    )
    assert result.passed is False
    assert result.composite_score == 0.0
    assert result.evaluator_version == EVALUATOR_VERSION
    assert result.content_hash == "sha256:bad"
    # Dimension scores should be empty (short-circuited).
    assert result.dimension_scores == {}


# --- Passing skill computes correct composite ---


def test_passing_skill_correct_composite(aggregator: ScoreAggregator) -> None:
    dimensions = {
        EvalDimension.CLARITY: [_dim_result(EvalDimension.CLARITY, 0.8)] * 3,
        EvalDimension.COMPLETENESS: [_dim_result(EvalDimension.COMPLETENESS, 0.7)] * 3,
        EvalDimension.SAFETY: [_dim_result(EvalDimension.SAFETY, 0.9)] * 3,
        EvalDimension.CORRECTNESS: [_dim_result(EvalDimension.CORRECTNESS, 0.6)] * 3,
    }

    result = aggregator.aggregate(
        structural=_passing_structural(),
        dimensions=dimensions,
    )

    # Expected: 0.25*0.8 + 0.30*0.7 + 0.25*0.9 + 0.20*0.6 = 0.2 + 0.21 + 0.225 + 0.12 = 0.755
    expected_composite = (
        DIMENSION_WEIGHTS["clarity"] * 0.8
        + DIMENSION_WEIGHTS["completeness"] * 0.7
        + DIMENSION_WEIGHTS["safety"] * 0.9
        + DIMENSION_WEIGHTS["correctness"] * 0.6
    )

    assert result.passed is True
    assert result.composite_score == pytest.approx(expected_composite)
    assert result.dimension_scores["clarity"] == pytest.approx(0.8)
    assert result.dimension_scores["completeness"] == pytest.approx(0.7)
    assert result.dimension_scores["safety"] == pytest.approx(0.9)
    assert result.dimension_scores["correctness"] == pytest.approx(0.6)
    assert result.evaluator_version == EVALUATOR_VERSION
    assert result.content_hash == "sha256:abc123"


# --- Median not mean (outlier resistance) ---


def test_median_not_mean_outlier_resistance(aggregator: ScoreAggregator) -> None:
    """A single outlier score should not drag the median."""
    # Three runs: 0.8, 0.8, 0.2 — mean=0.6, median=0.8.
    dimensions = {
        EvalDimension.CLARITY: [
            _dim_result(EvalDimension.CLARITY, 0.8),
            _dim_result(EvalDimension.CLARITY, 0.8),
            _dim_result(EvalDimension.CLARITY, 0.2),
        ],
        EvalDimension.COMPLETENESS: [_dim_result(EvalDimension.COMPLETENESS, 0.8)] * 3,
        EvalDimension.SAFETY: [_dim_result(EvalDimension.SAFETY, 0.8)] * 3,
        EvalDimension.CORRECTNESS: [_dim_result(EvalDimension.CORRECTNESS, 0.8)] * 3,
    }

    result = aggregator.aggregate(
        structural=_passing_structural(),
        dimensions=dimensions,
    )

    # Clarity median should be 0.8, not 0.6.
    assert result.dimension_scores["clarity"] == pytest.approx(0.8)


# --- Injection flagged on any dimension ---


def test_injection_flagged_on_any_dimension(aggregator: ScoreAggregator) -> None:
    """If any run on any dimension detects injection, the flag is set."""
    dimensions = {
        EvalDimension.CLARITY: [_dim_result(EvalDimension.CLARITY, 0.8)] * 3,
        EvalDimension.COMPLETENESS: [_dim_result(EvalDimension.COMPLETENESS, 0.8)] * 3,
        EvalDimension.SAFETY: [
            _dim_result(EvalDimension.SAFETY, 0.8),
            _dim_result(EvalDimension.SAFETY, 0.7, injection_detected=True),
            _dim_result(EvalDimension.SAFETY, 0.8),
        ],
        EvalDimension.CORRECTNESS: [_dim_result(EvalDimension.CORRECTNESS, 0.8)] * 3,
    }

    result = aggregator.aggregate(
        structural=_passing_structural(),
        dimensions=dimensions,
    )

    assert result.injection_flagged is True


def test_no_injection_when_none_detected(aggregator: ScoreAggregator) -> None:
    result = aggregator.aggregate(
        structural=_passing_structural(),
        dimensions=_uniform_dimensions(0.8),
    )
    assert result.injection_flagged is False


# --- Confidence from spread ---


def test_confidence_from_spread(aggregator: ScoreAggregator) -> None:
    """Wide score spread → low confidence."""
    dimensions = {
        EvalDimension.CLARITY: [
            _dim_result(EvalDimension.CLARITY, 0.3),
            _dim_result(EvalDimension.CLARITY, 0.9),
            _dim_result(EvalDimension.CLARITY, 0.6),
        ],
        EvalDimension.COMPLETENESS: [_dim_result(EvalDimension.COMPLETENESS, 0.8)] * 3,
        EvalDimension.SAFETY: [_dim_result(EvalDimension.SAFETY, 0.8)] * 3,
        EvalDimension.CORRECTNESS: [_dim_result(EvalDimension.CORRECTNESS, 0.8)] * 3,
    }

    result = aggregator.aggregate(
        structural=_passing_structural(),
        dimensions=dimensions,
    )

    # Clarity spread: 0.9 - 0.3 = 0.6 → confidence = 0.4.
    assert result.dimension_confidence["clarity"] == pytest.approx(0.4)
    # Other dimensions: spread = 0.0 → confidence = 1.0.
    assert result.dimension_confidence["completeness"] == pytest.approx(1.0)
    # Overall confidence = min across dimensions.
    assert result.overall_confidence == pytest.approx(0.4)


def test_uniform_scores_high_confidence(aggregator: ScoreAggregator) -> None:
    """Identical scores → confidence 1.0."""
    result = aggregator.aggregate(
        structural=_passing_structural(),
        dimensions=_uniform_dimensions(0.8),
    )
    assert result.overall_confidence == pytest.approx(1.0)
    for dim_conf in result.dimension_confidence.values():
        assert dim_conf == pytest.approx(1.0)


# --- Sandbox failure blocks pass ---


def test_sandbox_failure_blocks_pass(aggregator: ScoreAggregator) -> None:
    result = aggregator.aggregate(
        structural=_passing_structural(),
        dimensions=_uniform_dimensions(0.9),
        sandbox=SandboxResult(passed=False, errors=["timeout"]),
    )
    assert result.passed is False
    assert result.sandbox_passed is False
    # Composite score is still computed (just pass is blocked).
    assert result.composite_score > 0.0


def test_sandbox_success_does_not_block(aggregator: ScoreAggregator) -> None:
    result = aggregator.aggregate(
        structural=_passing_structural(),
        dimensions=_uniform_dimensions(0.9),
        sandbox=SandboxResult(passed=True, scenarios_run=1, scenarios_passed=1),
    )
    assert result.passed is True
    assert result.sandbox_passed is True


def test_sandbox_none_means_not_run(aggregator: ScoreAggregator) -> None:
    result = aggregator.aggregate(
        structural=_passing_structural(),
        dimensions=_uniform_dimensions(0.9),
        sandbox=None,
    )
    assert result.sandbox_passed is None


# --- Below threshold fails ---


def test_below_threshold_fails(aggregator: ScoreAggregator) -> None:
    # All dimensions at 0.4 → composite = 0.4 < PASS_THRESHOLD.
    result = aggregator.aggregate(
        structural=_passing_structural(),
        dimensions=_uniform_dimensions(0.4),
    )
    assert result.passed is False
    assert result.composite_score == pytest.approx(0.4)


def test_at_threshold_passes(aggregator: ScoreAggregator) -> None:
    result = aggregator.aggregate(
        structural=_passing_structural(),
        dimensions=_uniform_dimensions(PASS_THRESHOLD),
    )
    assert result.passed is True
    assert result.composite_score == pytest.approx(PASS_THRESHOLD)
