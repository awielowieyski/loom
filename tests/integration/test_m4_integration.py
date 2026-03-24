"""Integration tests for M4 Living Registry services."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from loom.db.repositories.usage_repo import UsageRepo
from loom.models.behavioral import (
    BehavioralRunResult,
    ComparativeAxisScores,
    ComparativeResult,
    ComparisonSummary,
    JudgeScore,
    RunnerOutput,
)
from loom.models.common import (
    AmendmentClassification,
    BehavioralEvalApplicability,
    EvalScenario,
    EvalSpec,
    TrustTier,
)
from loom.models.eval import EvalJob
from loom.services.amendment_triage import AmendmentTriagePipeline
from loom.services.behavioral_eval_service import BehavioralEvalService
from loom.services.rate_limiter import InMemoryRateLimiter, RateLimitExceeded
from loom.services.trust_service import TrustService
from tests.helpers import make_test_skill

if TYPE_CHECKING:
    import asyncpg


# ---------------------------------------------------------------------------
# Test 1: Behavioral eval pipeline (mock LLM)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_behavioral_eval_pipeline_mock_llm() -> None:
    """Real BehavioralEvalService with mock runner, judge, and repo."""
    skill = make_test_skill(
        eval_spec=EvalSpec(
            behavioral_eval=BehavioralEvalApplicability.REQUIRED,
            scenarios=[
                EvalScenario(
                    description="scenario 1",
                    input_context="user wants to deploy",
                    success_criteria="deployment succeeds",
                ),
                EvalScenario(
                    description="scenario 2",
                    input_context="user wants to rollback",
                    success_criteria="rollback completes",
                ),
            ],
        ),
    )

    runner_output = RunnerOutput(
        actions_taken=["step 1", "step 2"],
        output="done",
        artifacts=["artifact.txt"],
    )
    judge_score = JudgeScore(
        outcome_quality=0.85,
        completeness=0.80,
        efficiency=0.75,
        evidence="Good execution",
        confidence=0.90,
        injection_detected=False,
    )

    # Mock runner: returns RunnerOutput + latency
    mock_runner = AsyncMock()
    mock_runner.run = AsyncMock(return_value=(runner_output, 100))
    mock_runner._model_id = "test-runner-model"

    # Mock judge: returns JudgeScore + latency
    mock_judge = AsyncMock()
    mock_judge.judge = AsyncMock(return_value=(judge_score, 50))
    mock_judge._model_id = "test-judge-model"

    # Mock repo: returns a BehavioralRunResult
    mock_repo = AsyncMock()
    mock_repo.create_behavioral_run = AsyncMock(
        side_effect=lambda **kwargs: BehavioralRunResult(
            id=uuid.uuid4(),
            eval_job_id=kwargs["eval_job_id"],
            scenario_index=kwargs["scenario_index"],
            run_index=kwargs["run_index"],
            runner_output=RunnerOutput(**kwargs["runner_output"]),
            judge_score=kwargs["judge_score"],
            judge_evidence=JudgeScore(**kwargs["judge_evidence"]),
            judge_confidence=kwargs["judge_confidence"],
            injection_detected=kwargs["injection_detected"],
            runner_model_id=kwargs["runner_model_id"],
            judge_model_id=kwargs["judge_model_id"],
            runner_latency_ms=kwargs["runner_latency_ms"],
            judge_latency_ms=kwargs["judge_latency_ms"],
        )
    )

    service = BehavioralEvalService(
        runner=mock_runner,
        judge=mock_judge,
        behavioral_eval_repo=mock_repo,
        runs_per_scenario=3,
    )

    eval_job_id = uuid.uuid4()
    result = await service.run_evaluation(skill, eval_job_id)

    assert result is not None
    # 2 scenarios x 3 runs = 6 total runs
    assert result.run_count == 6
    assert result.scenario_count == 2
    assert result.behavioral_score > 0
    # Median of [0.8, 0.8, 0.8, 0.8, 0.8, 0.8] = 0.8  (mean of 0.85, 0.80, 0.75)
    assert abs(result.behavioral_score - 0.8) < 0.01
    assert len(result.per_run) == 6


# ---------------------------------------------------------------------------
# Test 2: Usage report round-trip (real DB)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_usage_report_round_trip(
    db_conn: asyncpg.Connection,
    test_skill_id: uuid.UUID,
) -> None:
    """Create usage reports in DB, then aggregate and verify success rate."""
    repo = UsageRepo(db_conn)

    # Report 3 outcomes: 2 success, 1 failure
    outcomes = [
        ("success", "key-1"),
        ("success", "key-2"),
        ("failure", "key-3"),
    ]
    for outcome, key in outcomes:
        await repo.create_usage_report(
            skill_id=test_skill_id,
            skill_version="1.0.0",
            outcome=outcome,
            runtime_ms=200,
            idempotency_key=key,
        )

    # Verify reports are persisted
    reports = await repo.get_reports_for_skill(test_skill_id)
    assert len(reports) == 3

    # Aggregate manually
    now = datetime.now(UTC)
    window_start = datetime(2020, 1, 1, tzinfo=UTC)
    agg_data = await repo.aggregate_reports_in_window(test_skill_id, "1.0.0", window_start)

    success_count = agg_data["success"]
    failure_count = agg_data["failure"]
    total = success_count + failure_count
    success_rate = success_count / total if total > 0 else 0.0

    assert success_count == 2
    assert failure_count == 1
    assert abs(success_rate - 0.67) < 0.01

    # Persist aggregate via upsert
    aggregate = await repo.upsert_aggregate(
        skill_id=test_skill_id,
        skill_version="1.0.0",
        window_type="7d",
        success_count=success_count,
        partial_count=0,
        failure_count=failure_count,
        success_rate=success_rate,
        avg_runtime_ms=200.0,
        computed_at=now,
        window_start=window_start,
    )
    assert abs(aggregate.success_rate - 0.67) < 0.01


# ---------------------------------------------------------------------------
# Test 3: Amendment triage — refinement path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_amendment_triage_refinement() -> None:
    """High similarity + new >= old -> refinement."""
    old_skill = make_test_skill(slug="skill-old")
    new_skill = make_test_skill(slug="skill-new")

    scenarios = [
        EvalScenario(
            description="test scenario",
            input_context="test context",
            success_criteria="should pass",
        ),
    ]

    # Mock embedder returning nearly identical embeddings (cosine ~ 0.97)
    # Use unit vectors that are close: [1, 0.1] and [1, 0.12] => high similarity
    mock_embedder = AsyncMock()
    call_count = 0

    async def _embed(content: str) -> list[float]:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return [1.0, 0.1, 0.0]  # old
        return [1.0, 0.12, 0.0]  # new (very similar)

    mock_embedder.embed = AsyncMock(side_effect=_embed)

    # Mock comparative eval: new (b) wins or ties -> new is at least as good
    mock_comparative = AsyncMock()
    comparison = ComparisonSummary(
        skill_a_id=old_skill.id,
        skill_b_id=new_skill.id,
        per_scenario=[
            ComparativeResult(
                id=uuid.uuid4(),
                skill_a_id=old_skill.id,
                skill_a_version="1.0.0",
                skill_b_id=new_skill.id,
                skill_b_version="1.0.0",
                scenario_index=0,
                winner="b",
                score_a=ComparativeAxisScores(
                    outcome_quality=0.7, completeness=0.7, efficiency=0.7, safety=0.9
                ),
                score_b=ComparativeAxisScores(
                    outcome_quality=0.85, completeness=0.85, efficiency=0.85, safety=0.9
                ),
                preference_confidence=0.85,
                reasoning="B is better",
            ),
        ],
        overall_winner="b",
        win_count_a=0,
        win_count_b=1,
        tie_count=0,
    )
    mock_comparative.compare = AsyncMock(return_value=comparison)

    pipeline = AmendmentTriagePipeline(
        embedder=mock_embedder,
        comparative_eval=mock_comparative,
    )

    result = await pipeline.triage(old_skill, new_skill, scenarios)
    assert result.classification == AmendmentClassification.REFINEMENT
    assert result.semantic_similarity > 0.95


# ---------------------------------------------------------------------------
# Test 4: Amendment triage — regression path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_amendment_triage_regression() -> None:
    """High similarity + old > new -> regression."""
    old_skill = make_test_skill(slug="skill-old")
    new_skill = make_test_skill(slug="skill-new")

    scenarios = [
        EvalScenario(
            description="test scenario",
            input_context="test context",
            success_criteria="should pass",
        ),
    ]

    # Same high-similarity embeddings
    mock_embedder = AsyncMock()
    call_count = 0

    async def _embed(content: str) -> list[float]:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return [1.0, 0.1, 0.0]
        return [1.0, 0.12, 0.0]

    mock_embedder.embed = AsyncMock(side_effect=_embed)

    # Mock comparative eval: old (a) wins -> regression
    mock_comparative = AsyncMock()
    comparison = ComparisonSummary(
        skill_a_id=old_skill.id,
        skill_b_id=new_skill.id,
        per_scenario=[
            ComparativeResult(
                id=uuid.uuid4(),
                skill_a_id=old_skill.id,
                skill_a_version="1.0.0",
                skill_b_id=new_skill.id,
                skill_b_version="1.0.0",
                scenario_index=0,
                winner="a",
                score_a=ComparativeAxisScores(
                    outcome_quality=0.9, completeness=0.9, efficiency=0.9, safety=0.9
                ),
                score_b=ComparativeAxisScores(
                    outcome_quality=0.5, completeness=0.5, efficiency=0.5, safety=0.9
                ),
                preference_confidence=0.90,
                reasoning="A is clearly better",
            ),
        ],
        overall_winner="a",
        win_count_a=1,
        win_count_b=0,
        tie_count=0,
    )
    mock_comparative.compare = AsyncMock(return_value=comparison)

    pipeline = AmendmentTriagePipeline(
        embedder=mock_embedder,
        comparative_eval=mock_comparative,
    )

    result = await pipeline.triage(old_skill, new_skill, scenarios)
    assert result.classification == AmendmentClassification.REGRESSION
    assert result.semantic_similarity > 0.95


# ---------------------------------------------------------------------------
# Test 5: Trust promotion with behavioral score
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trust_promotion_with_behavioral_score() -> None:
    """Behavioral score gates trust-tier promotion."""
    skill_id = uuid.uuid4()

    # Mock eval_repo returning a passing eval job
    mock_eval_repo = AsyncMock()
    mock_eval_job = MagicMock(spec=EvalJob)
    mock_eval_job.composite_score = 0.85
    mock_eval_job.injection_flagged = False
    mock_eval_job.dimension_scores = {"safety": 0.90, "correctness": 0.85}
    mock_eval_repo.get_latest_eval_for_skill = AsyncMock(return_value=mock_eval_job)

    service = TrustService(eval_repo=mock_eval_repo)

    # Case 1: behavioral_score=0.75 (above floor of 0.60) -> should promote
    decision = await service.check_promotion(
        skill_id=skill_id,
        current_tier=TrustTier.EXPERIMENTAL,
        is_signed=True,
        usage_count=50,
        success_rate=0.95,
        behavioral_score=0.75,
    )
    assert decision.should_promote is True
    assert decision.target_tier == TrustTier.COMMUNITY

    # Case 2: behavioral_score=0.40 (below floor of 0.60) -> should NOT promote
    decision = await service.check_promotion(
        skill_id=skill_id,
        current_tier=TrustTier.EXPERIMENTAL,
        is_signed=True,
        usage_count=50,
        success_rate=0.95,
        behavioral_score=0.40,
    )
    assert decision.should_promote is False
    assert "behavioral" in decision.reason.lower()


# ---------------------------------------------------------------------------
# Test 6: Deprecation workflow (real DB)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deprecation_workflow(
    db_conn: asyncpg.Connection,
    test_skill_id: uuid.UUID,
) -> None:
    """Mark a skill as deprecated and verify fields are set."""
    from loom.db.repositories.skill_repo import SkillRepo

    repo = SkillRepo(db_conn)

    # Verify not deprecated initially
    row = await db_conn.fetchrow(
        "SELECT deprecated_at, successor_slug FROM skills WHERE id = $1",
        test_skill_id,
    )
    assert row["deprecated_at"] is None

    # Deprecate with a successor slug
    await repo.mark_deprecated(test_skill_id, successor_slug="better-skill-v2")

    # Verify deprecated_at is set and successor_slug matches
    row = await db_conn.fetchrow(
        "SELECT deprecated_at, successor_slug FROM skills WHERE id = $1",
        test_skill_id,
    )
    assert row["deprecated_at"] is not None
    assert row["successor_slug"] == "better-skill-v2"


# ---------------------------------------------------------------------------
# Test 7: Rate limiter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_in_memory_rate_limiter() -> None:
    """InMemoryRateLimiter enforces limits and raises on exceed."""
    limiter = InMemoryRateLimiter(
        unverified_limit=5,
        verified_limit=20,
        window_seconds=3600,
    )

    author = "test-author-123"

    # Make 5 requests (should all pass)
    for _ in range(5):
        await limiter.check_rate_limit(author, is_verified=False)

    # 6th request should raise
    with pytest.raises(RateLimitExceeded) as exc_info:
        await limiter.check_rate_limit(author, is_verified=False)

    assert exc_info.value.retry_after_seconds > 0

    # Verify the internal state: 5 entries (the 6th was rejected)
    assert len(limiter._entries[author]) == 5
