"""Tests for BehavioralEvalRepo — behavioral runs, comparative results, rankings."""

import uuid

import asyncpg
import pytest

from loom.db.repositories.behavioral_eval_repo import BehavioralEvalRepo
from loom.db.repositories.eval_repo import EvalRepo


@pytest.fixture
def behavioral_repo(db_conn: asyncpg.Connection) -> BehavioralEvalRepo:
    return BehavioralEvalRepo(db_conn)


@pytest.fixture
def eval_repo(db_conn: asyncpg.Connection) -> EvalRepo:
    return EvalRepo(db_conn)


@pytest.fixture
async def eval_job_id(eval_repo: EvalRepo, test_skill_id: uuid.UUID) -> uuid.UUID:
    job = await eval_repo.create_eval_job(
        skill_id=test_skill_id,
        skill_version="1.0.0",
        content_hash="sha256:behavioral_test",
        trigger_type="submission",
        evaluator_version="v0.2.0",
    )
    return job.id


@pytest.mark.asyncio
async def test_create_behavioral_run(
    behavioral_repo: BehavioralEvalRepo, eval_job_id: uuid.UUID
) -> None:
    run = await behavioral_repo.create_behavioral_run(
        eval_job_id=eval_job_id,
        scenario_index=0,
        run_index=0,
        runner_output={"actions_taken": ["step1"], "output": "done", "artifacts": []},
        judge_score=0.85,
        judge_evidence={
            "outcome_quality": 0.9,
            "completeness": 0.8,
            "efficiency": 0.85,
            "evidence": "Good work",
            "confidence": 0.9,
            "injection_detected": False,
        },
        judge_confidence=0.9,
        injection_detected=False,
        runner_model_id="gpt-4o-mini",
        judge_model_id="gpt-4o",
        runner_latency_ms=500,
        judge_latency_ms=300,
    )
    assert run.eval_job_id == eval_job_id
    assert run.scenario_index == 0
    assert run.judge_score == 0.85
    assert run.runner_model_id == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_get_runs_ordered(
    behavioral_repo: BehavioralEvalRepo, eval_job_id: uuid.UUID
) -> None:
    for scenario in range(2):
        for run_idx in range(2):
            await behavioral_repo.create_behavioral_run(
                eval_job_id=eval_job_id,
                scenario_index=scenario,
                run_index=run_idx,
                runner_output={"actions_taken": [], "output": "ok", "artifacts": []},
                judge_score=0.7 + scenario * 0.1,
                judge_evidence={
                    "outcome_quality": 0.8,
                    "completeness": 0.7,
                    "efficiency": 0.7,
                    "evidence": "ok",
                    "confidence": 0.8,
                    "injection_detected": False,
                },
                judge_confidence=0.8,
                runner_model_id="model-a",
                judge_model_id="model-b",
            )
    runs = await behavioral_repo.get_runs_for_job(eval_job_id)
    assert len(runs) == 4
    assert runs[0].scenario_index == 0 and runs[0].run_index == 0
    assert runs[3].scenario_index == 1 and runs[3].run_index == 1


@pytest.mark.asyncio
async def test_create_comparative_result(
    behavioral_repo: BehavioralEvalRepo,
    test_skill_id: uuid.UUID,
    test_author_id: uuid.UUID,
    test_category_id: uuid.UUID,
    db_conn: asyncpg.Connection,
) -> None:
    # Create a second skill
    skill_b_id = uuid.uuid4()
    await db_conn.execute(
        """
        INSERT INTO skills (
            id, slug, name, description, content, category_id, tags,
            scope, version, author_id, trust_tier, cost_profile,
            cost_drivers, estimated_duration, dependencies, eval_spec
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7,
            $8, $9, $10, $11, $12,
            $13, $14, $15, $16
        )
        """,
        skill_b_id,
        "test-skill-b",
        "Test Skill B",
        "Another skill",
        "# Test B\nDo another thing.",
        test_category_id,
        [],
        "community",
        "1.0.0",
        test_author_id,
        "experimental",
        "free",
        [],
        "fast",
        {},
        {},
    )

    result = await behavioral_repo.create_comparative_result(
        skill_a_id=test_skill_id,
        skill_a_version="1.0.0",
        skill_b_id=skill_b_id,
        skill_b_version="1.0.0",
        scenario_index=0,
        winner="a",
        score_a={"outcome_quality": 0.9, "completeness": 0.85, "efficiency": 0.8, "safety": 1.0},
        score_b={"outcome_quality": 0.7, "completeness": 0.6, "efficiency": 0.7, "safety": 1.0},
        preference_confidence=0.8,
        reasoning="Skill A had better quality output",
        classification="refinement",
        judge_model_id="gpt-4o",
    )
    assert result.winner == "a"
    assert result.skill_a_id == test_skill_id
    assert result.preference_confidence == 0.8

    # Verify get_comparisons_for_skill returns it
    comps = await behavioral_repo.get_comparisons_for_skill(test_skill_id)
    assert len(comps) == 1
    comps_b = await behavioral_repo.get_comparisons_for_skill(skill_b_id)
    assert len(comps_b) == 1


@pytest.mark.asyncio
async def test_upsert_ranking(
    behavioral_repo: BehavioralEvalRepo,
    test_skill_id: uuid.UUID,
    test_category_id: uuid.UUID,
) -> None:
    ranking = await behavioral_repo.upsert_ranking(
        skill_id=test_skill_id,
        category_id=test_category_id,
        rating=1250.0,
        matches_played=5,
        wins=3,
        losses=1,
        ties=1,
    )
    assert ranking.rating == 1250.0
    assert ranking.matches_played == 5

    # Update
    ranking2 = await behavioral_repo.upsert_ranking(
        skill_id=test_skill_id,
        category_id=test_category_id,
        rating=1300.0,
        matches_played=6,
        wins=4,
        losses=1,
        ties=1,
    )
    assert ranking2.id == ranking.id
    assert ranking2.rating == 1300.0

    # Verify get_ranking
    fetched = await behavioral_repo.get_ranking(test_skill_id, test_category_id)
    assert fetched is not None
    assert fetched.rating == 1300.0
