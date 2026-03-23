"""Tests for EvalPipelineService orchestrator."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from loom.models.common import (
    CostProfile,
    DependencyDeclaration,
    EvalDimension,
    EvalScenario,
    EvalSpec,
    TrustTier,
)
from loom.models.eval import (
    DimensionResult,
    EvalResult,
    IsolatedFragments,
    SandboxResult,
    StructuralReport,
)
from loom.models.skill import Skill
from loom.services.eval_pipeline import EvalPipelineService


def _make_skill(**overrides: Any) -> Skill:
    """Create a valid Skill for pipeline testing."""
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "slug": "test-skill",
        "name": "Test Skill",
        "description": "A test skill",
        "content": "# Step 1\n\nThis is valid content that is long enough.",
        "category_id": uuid.uuid4(),
        "tags": ["test"],
        "scope": "community",
        "version": "1.0.0",
        "author_id": uuid.uuid4(),
        "trust_tier": TrustTier.EXPERIMENTAL,
        "cost_profile": CostProfile.FREE,
        "cost_drivers": [],
        "estimated_duration": "fast",
        "dependencies": DependencyDeclaration(),
        "eval_spec": EvalSpec(
            scenarios=[
                EvalScenario(
                    description="basic test",
                    input_context="test context",
                    success_criteria="should pass",
                )
            ]
        ),
    }
    defaults.update(overrides)
    return Skill(**defaults)


def _passing_structural(content_hash: str = "sha256:abc123") -> StructuralReport:
    return StructuralReport(passed=True, content_hash=content_hash)


def _failing_structural() -> StructuralReport:
    return StructuralReport(
        passed=False,
        errors=["content too short"],
        content_hash="sha256:bad",
    )


def _dim_result(dim: EvalDimension, score: float = 0.8) -> DimensionResult:
    return DimensionResult(
        dimension=dim,
        score=score,
        evidence=["test evidence"],
        confidence=0.9,
    )


def _passing_dimensions() -> dict[str, list[DimensionResult]]:
    """LLM evaluator returns str-keyed results."""
    return {dim.value: [_dim_result(dim) for _ in range(3)] for dim in EvalDimension}


def _make_fragments() -> IsolatedFragments:
    return IsolatedFragments(
        content_hash="sha256:abc123",
        metadata={"name": "Test Skill"},
        step_outline=["# Step 1"],
        full_body="# Step 1\n\nContent",
    )


def _passing_eval_result() -> EvalResult:
    return EvalResult(
        passed=True,
        composite_score=0.8,
        dimension_scores={d.value: 0.8 for d in EvalDimension},
        dimension_confidence={d.value: 1.0 for d in EvalDimension},
        overall_confidence=1.0,
        content_hash="sha256:abc123",
        evaluator_version="m2-v0.1.0",
    )


def _failed_eval_result() -> EvalResult:
    return EvalResult(
        passed=False,
        composite_score=0.0,
        content_hash="sha256:bad",
        evaluator_version="m2-v0.1.0",
    )


@pytest.fixture
def static_analyser() -> MagicMock:
    mock = MagicMock()
    mock.analyse.return_value = _passing_structural()
    return mock


@pytest.fixture
def llm_evaluator() -> AsyncMock:
    mock = AsyncMock()
    mock.evaluate_all.return_value = _passing_dimensions()
    return mock


@pytest.fixture
def score_aggregator() -> MagicMock:
    mock = MagicMock()
    mock.aggregate.return_value = _passing_eval_result()
    return mock


@pytest.fixture
def sandbox_runner() -> AsyncMock:
    mock = AsyncMock()
    mock.execute.return_value = SandboxResult(passed=True, scenarios_run=1, scenarios_passed=1)
    return mock


@pytest.fixture
def content_isolator() -> MagicMock:
    mock = MagicMock()
    mock.return_value = _make_fragments()
    return mock


@pytest.fixture
def pipeline(
    static_analyser: MagicMock,
    content_isolator: MagicMock,
    llm_evaluator: AsyncMock,
    score_aggregator: MagicMock,
) -> EvalPipelineService:
    """Pipeline without sandbox runner."""
    return EvalPipelineService(
        static_analyser=static_analyser,
        content_isolator=content_isolator,
        llm_evaluator=llm_evaluator,
        score_aggregator=score_aggregator,
        sandbox_runner=None,
    )


@pytest.fixture
def pipeline_with_sandbox(
    static_analyser: MagicMock,
    content_isolator: MagicMock,
    llm_evaluator: AsyncMock,
    score_aggregator: MagicMock,
    sandbox_runner: AsyncMock,
) -> EvalPipelineService:
    """Pipeline with sandbox runner."""
    return EvalPipelineService(
        static_analyser=static_analyser,
        content_isolator=content_isolator,
        llm_evaluator=llm_evaluator,
        score_aggregator=score_aggregator,
        sandbox_runner=sandbox_runner,
    )


# --- Full pipeline passes ---


@pytest.mark.asyncio
async def test_full_pipeline_passes(
    pipeline: EvalPipelineService,
    static_analyser: MagicMock,
    content_isolator: MagicMock,
    llm_evaluator: AsyncMock,
    score_aggregator: MagicMock,
) -> None:
    skill = _make_skill()

    result, structural, raw_dims = await pipeline.evaluate(skill)

    assert result.passed is True
    assert result.composite_score == 0.8

    # All phases called.
    static_analyser.analyse.assert_called_once()
    content_isolator.assert_called_once()
    llm_evaluator.evaluate_all.assert_called_once()
    score_aggregator.aggregate.assert_called_once()


# --- Structural failure short-circuits ---


@pytest.mark.asyncio
async def test_structural_failure_short_circuits(
    static_analyser: MagicMock,
    content_isolator: MagicMock,
    llm_evaluator: AsyncMock,
    score_aggregator: MagicMock,
) -> None:
    static_analyser.analyse.return_value = _failing_structural()
    score_aggregator.aggregate.return_value = _failed_eval_result()

    pipeline = EvalPipelineService(
        static_analyser=static_analyser,
        content_isolator=content_isolator,
        llm_evaluator=llm_evaluator,
        score_aggregator=score_aggregator,
    )

    skill = _make_skill()
    result, structural, raw_dims = await pipeline.evaluate(skill)

    assert result.passed is False
    assert raw_dims == {}

    # Static analyser called.
    static_analyser.analyse.assert_called_once()

    # LLM evaluator NOT called (short-circuited).
    llm_evaluator.evaluate_all.assert_not_called()

    # Score aggregator called with empty dimensions.
    score_aggregator.aggregate.assert_called_once()
    agg_call = score_aggregator.aggregate.call_args
    assert agg_call.kwargs["dimensions"] == {}


# --- Phases called in correct order ---


@pytest.mark.asyncio
async def test_phases_called_in_correct_order(
    static_analyser: MagicMock,
    llm_evaluator: AsyncMock,
    score_aggregator: MagicMock,
) -> None:
    call_order: list[str] = []

    def track_analyse(*args: Any, **kwargs: Any) -> StructuralReport:
        call_order.append("static_analyser")
        return _passing_structural()

    def track_isolate(*args: Any, **kwargs: Any) -> IsolatedFragments:
        call_order.append("content_isolator")
        return _make_fragments()

    async def track_evaluate_all(*args: Any, **kwargs: Any) -> dict[str, list[DimensionResult]]:
        call_order.append("llm_evaluator")
        return _passing_dimensions()

    def track_aggregate(*args: Any, **kwargs: Any) -> EvalResult:
        call_order.append("score_aggregator")
        return _passing_eval_result()

    static_analyser.analyse.side_effect = track_analyse
    llm_evaluator.evaluate_all.side_effect = track_evaluate_all
    score_aggregator.aggregate.side_effect = track_aggregate

    mock_isolator = MagicMock(side_effect=track_isolate)

    pipeline = EvalPipelineService(
        static_analyser=static_analyser,
        content_isolator=mock_isolator,
        llm_evaluator=llm_evaluator,
        score_aggregator=score_aggregator,
    )

    await pipeline.evaluate(_make_skill())

    assert call_order == [
        "static_analyser",
        "content_isolator",
        "llm_evaluator",
        "score_aggregator",
    ]


# --- Sandbox runner optional (None) ---


@pytest.mark.asyncio
async def test_sandbox_runner_optional_none(
    pipeline: EvalPipelineService,
    score_aggregator: MagicMock,
) -> None:
    await pipeline.evaluate(_make_skill())

    # Score aggregator called with sandbox=None.
    agg_call = score_aggregator.aggregate.call_args
    assert agg_call.kwargs.get("sandbox") is None


# --- Sandbox runner called when provided ---


@pytest.mark.asyncio
async def test_sandbox_runner_called_when_provided(
    pipeline_with_sandbox: EvalPipelineService,
    sandbox_runner: AsyncMock,
    score_aggregator: MagicMock,
) -> None:
    await pipeline_with_sandbox.evaluate(_make_skill())

    sandbox_runner.execute.assert_called_once()

    # Score aggregator receives sandbox result.
    agg_call = score_aggregator.aggregate.call_args
    assert agg_call.kwargs["sandbox"] is not None
    assert agg_call.kwargs["sandbox"].passed is True
