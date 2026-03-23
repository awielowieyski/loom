"""Tests for EvalRepo — eval jobs, dimension runs, and trust audit persistence."""

import uuid

import asyncpg
import pytest

from loom.db.repositories.eval_repo import EvalRepo


@pytest.fixture
def eval_repo(db_conn: asyncpg.Connection) -> EvalRepo:
    return EvalRepo(db_conn)


@pytest.mark.asyncio
async def test_create_and_get_eval_job(eval_repo: EvalRepo, test_skill_id: uuid.UUID) -> None:
    job = await eval_repo.create_eval_job(
        skill_id=test_skill_id,
        skill_version="1.0.0",
        content_hash="sha256:abc123",
        trigger_type="submission",
        evaluator_version="v0.1.0",
    )
    assert job.skill_id == test_skill_id
    assert job.status == "pending"
    assert job.trigger_type == "submission"
    assert job.evaluator_version == "v0.1.0"

    fetched = await eval_repo.get_eval_job(job.id)
    assert fetched is not None
    assert fetched.id == job.id
    assert fetched.content_hash == "sha256:abc123"


@pytest.mark.asyncio
async def test_get_eval_job_not_found(eval_repo: EvalRepo) -> None:
    result = await eval_repo.get_eval_job(uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_update_eval_job_status(eval_repo: EvalRepo, test_skill_id: uuid.UUID) -> None:
    job = await eval_repo.create_eval_job(
        skill_id=test_skill_id,
        skill_version="1.0.0",
        content_hash="sha256:def456",
        trigger_type="amendment",
        evaluator_version="v0.1.0",
    )
    updated = await eval_repo.update_eval_job(
        job.id,
        status="completed",
        composite_score=0.85,
        dimension_scores={"clarity": 0.9, "completeness": 0.8},
        dimension_confidence={"clarity": 0.95, "completeness": 0.90},
        injection_flagged=False,
        overall_confidence=0.90,
    )
    assert updated is not None
    assert updated.status == "completed"
    assert updated.composite_score == 0.85
    assert updated.dimension_scores == {"clarity": 0.9, "completeness": 0.8}
    assert updated.overall_confidence == 0.90


@pytest.mark.asyncio
async def test_create_dimension_run(eval_repo: EvalRepo, test_skill_id: uuid.UUID) -> None:
    job = await eval_repo.create_eval_job(
        skill_id=test_skill_id,
        skill_version="1.0.0",
        content_hash="sha256:ghi789",
        trigger_type="submission",
        evaluator_version="v0.1.0",
    )
    run = await eval_repo.create_dimension_run(
        eval_job_id=job.id,
        dimension="clarity",
        run_index=0,
        score=0.85,
        evidence=["Clear step headings", "Good structure"],
        injection_detected=False,
        confidence=0.95,
        prompt_variant="clarity_v1",
        model_id="gpt-4o-mini",
    )
    assert run.eval_job_id == job.id
    assert run.dimension == "clarity"
    assert run.run_index == 0
    assert run.score == 0.85
    assert run.evidence == ["Clear step headings", "Good structure"]


@pytest.mark.asyncio
async def test_get_runs_for_job(eval_repo: EvalRepo, test_skill_id: uuid.UUID) -> None:
    job = await eval_repo.create_eval_job(
        skill_id=test_skill_id,
        skill_version="1.0.0",
        content_hash="sha256:jkl012",
        trigger_type="submission",
        evaluator_version="v0.1.0",
    )
    for i in range(3):
        await eval_repo.create_dimension_run(
            eval_job_id=job.id,
            dimension="clarity",
            run_index=i,
            score=0.80 + i * 0.05,
            evidence=[f"Evidence {i}"],
            injection_detected=False,
            confidence=0.90,
            prompt_variant="clarity_v1",
            model_id="gpt-4o-mini",
        )
    runs = await eval_repo.get_runs_for_job(job.id)
    assert len(runs) == 3
    assert runs[0].run_index == 0
    assert runs[2].run_index == 2


@pytest.mark.asyncio
async def test_get_latest_eval_for_skill(eval_repo: EvalRepo, test_skill_id: uuid.UUID) -> None:
    # Create a single job and verify it is returned as the latest
    job = await eval_repo.create_eval_job(
        skill_id=test_skill_id,
        skill_version="1.0.0",
        content_hash="sha256:only",
        trigger_type="submission",
        evaluator_version="v0.1.0",
    )
    latest = await eval_repo.get_latest_eval_for_skill(test_skill_id)
    assert latest is not None
    assert latest.id == job.id
    assert latest.content_hash == "sha256:only"


@pytest.mark.asyncio
async def test_get_latest_eval_for_skill_not_found(eval_repo: EvalRepo) -> None:
    result = await eval_repo.get_latest_eval_for_skill(uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_create_trust_audit_entry(eval_repo: EvalRepo, test_skill_id: uuid.UUID) -> None:
    entry = await eval_repo.create_trust_audit_entry(
        skill_id=test_skill_id,
        previous_tier="experimental",
        new_tier="community",
        reason="auto_promotion",
    )
    assert entry.skill_id == test_skill_id
    assert entry.previous_tier == "experimental"
    assert entry.new_tier == "community"
    assert entry.reason == "auto_promotion"
    assert entry.eval_job_id is None


@pytest.mark.asyncio
async def test_get_trust_history(eval_repo: EvalRepo, test_skill_id: uuid.UUID) -> None:
    await eval_repo.create_trust_audit_entry(
        skill_id=test_skill_id,
        previous_tier="experimental",
        new_tier="community",
        reason="auto_promotion",
    )
    await eval_repo.create_trust_audit_entry(
        skill_id=test_skill_id,
        previous_tier="community",
        new_tier="verified",
        reason="manual_promotion",
    )
    history = await eval_repo.get_trust_history(test_skill_id)
    assert len(history) == 2
    tiers = {e.new_tier for e in history}
    assert tiers == {"community", "verified"}
