"""Tests for the scheduled_reeval cron job."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from loom.models.skill import Skill


def _make_skill(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "slug": f"skill-{uuid.uuid4().hex[:6]}",
        "name": "Test Skill",
        "description": "A test skill",
        "content": "# test",
        "category_id": uuid.uuid4(),
        "tags": [],
        "scope": "community",
        "version": "1.0.0",
        "author_id": uuid.uuid4(),
        "trust_tier": "community",
        "cost_profile": "free",
        "cost_drivers": [],
        "estimated_duration": "fast",
    }
    defaults.update(overrides)
    return Skill(**defaults)


class _FakeAcquire:
    """Async context manager that yields a mock connection."""

    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, *exc):
        return False


@pytest.fixture
def ctx():
    """Build a minimal worker context dict for scheduled_reeval."""
    conn = AsyncMock()
    pool = MagicMock()
    pool.acquire.return_value = _FakeAcquire(conn)

    skill_repo = AsyncMock()
    settings = MagicMock()
    settings.pipeline.reeval_sample_percent = 0.20

    redis = AsyncMock()

    return {
        "pool": pool,
        "settings": settings,
        "skill_repo_factory": MagicMock(return_value=skill_repo),
        "redis": redis,
        "_skill_repo": skill_repo,
    }


@pytest.mark.asyncio
async def test_scheduled_reeval_no_eligible_skills(ctx):
    """When no eligible skills exist, nothing is enqueued."""
    from loom.worker import scheduled_reeval

    ctx["_skill_repo"].count_by_trust_tiers.return_value = 0

    result = await scheduled_reeval(ctx)

    assert result == {"skills_sampled": 0, "total_eligible": 0}
    ctx["redis"].enqueue_job.assert_not_called()


@pytest.mark.asyncio
async def test_scheduled_reeval_samples_correct_percent(ctx):
    """20% sample of 10 skills => ceil(2) = 2 skills enqueued."""
    from loom.worker import scheduled_reeval

    skills = [_make_skill() for _ in range(2)]
    ctx["_skill_repo"].count_by_trust_tiers.return_value = 10
    ctx["_skill_repo"].get_reeval_candidates.return_value = skills

    result = await scheduled_reeval(ctx)

    assert result["skills_sampled"] == 2
    assert result["total_eligible"] == 10
    ctx["_skill_repo"].get_reeval_candidates.assert_called_once_with(["community", "verified"], 2)
    assert ctx["redis"].enqueue_job.call_count == 2


@pytest.mark.asyncio
async def test_scheduled_reeval_enqueues_with_scheduled_trigger(ctx):
    """Each enqueued job uses trigger='scheduled'."""
    from loom.worker import scheduled_reeval

    skill = _make_skill()
    ctx["_skill_repo"].count_by_trust_tiers.return_value = 1
    ctx["_skill_repo"].get_reeval_candidates.return_value = [skill]

    await scheduled_reeval(ctx)

    ctx["redis"].enqueue_job.assert_called_once_with("run_eval_job", str(skill.id), "scheduled")


@pytest.mark.asyncio
async def test_scheduled_reeval_minimum_sample_one(ctx):
    """Even with 1 skill at 20%, sample size is at least 1."""
    from loom.worker import scheduled_reeval

    skill = _make_skill()
    ctx["_skill_repo"].count_by_trust_tiers.return_value = 1
    ctx["_skill_repo"].get_reeval_candidates.return_value = [skill]

    result = await scheduled_reeval(ctx)

    assert result["skills_sampled"] == 1
    ctx["_skill_repo"].get_reeval_candidates.assert_called_once_with(["community", "verified"], 1)
