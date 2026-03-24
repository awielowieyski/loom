"""Tests for the DriftDetector service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from loom.models.drift import DriftReport, ModelDriftReport
from loom.models.eval import EvalJob
from loom.services.drift_detector import DriftDetector


def _make_eval_job(
    skill_id: uuid.UUID | None = None,
    composite_score: float | None = 0.75,
    evaluator_version: str = "v1.0",
    **overrides,
) -> EvalJob:
    defaults = {
        "id": uuid.uuid4(),
        "skill_id": skill_id or uuid.uuid4(),
        "skill_version": "1.0.0",
        "content_hash": "abc123",
        "trigger_type": "submission",
        "status": "completed",
        "composite_score": composite_score,
        "evaluator_version": evaluator_version,
        "completed_at": datetime.now(UTC),
        "created_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return EvalJob(**defaults)


@pytest.mark.asyncio
async def test_score_drift_below_threshold_returns_none():
    """Small score changes below threshold return None."""
    skill_id = uuid.uuid4()
    new_job = _make_eval_job(skill_id=skill_id, composite_score=0.75)
    old_job = _make_eval_job(skill_id=skill_id, composite_score=0.72)

    repo = AsyncMock()
    repo.get_eval_job.return_value = new_job
    repo.get_recent_completed_jobs.return_value = [new_job, old_job]

    detector = DriftDetector(repo, drift_threshold=0.15)
    result = await detector.check_score_drift(skill_id, new_job.id)

    assert result is None


@pytest.mark.asyncio
async def test_score_drift_above_threshold_returns_report():
    """Large score changes above threshold return a DriftReport."""
    skill_id = uuid.uuid4()
    new_job = _make_eval_job(skill_id=skill_id, composite_score=0.90)
    old_job = _make_eval_job(skill_id=skill_id, composite_score=0.50)

    repo = AsyncMock()
    repo.get_eval_job.return_value = new_job
    repo.get_recent_completed_jobs.return_value = [new_job, old_job]

    detector = DriftDetector(repo, drift_threshold=0.15)
    result = await detector.check_score_drift(skill_id, new_job.id)

    assert result is not None
    assert isinstance(result, DriftReport)
    assert result.exceeds_threshold is True
    assert result.old_score == 0.50
    assert result.new_score == 0.90
    assert abs(result.delta - 0.40) < 1e-9


@pytest.mark.asyncio
async def test_score_drift_fewer_than_two_jobs_returns_none():
    """If a skill has only one job, no drift can be detected."""
    skill_id = uuid.uuid4()
    new_job = _make_eval_job(skill_id=skill_id, composite_score=0.80)

    repo = AsyncMock()
    repo.get_eval_job.return_value = new_job
    repo.get_recent_completed_jobs.return_value = [new_job]

    detector = DriftDetector(repo, drift_threshold=0.15)
    result = await detector.check_score_drift(skill_id, new_job.id)

    assert result is None


@pytest.mark.asyncio
async def test_model_drift_detected():
    """MAD across version groups above threshold reports drift."""
    skill_a = uuid.uuid4()
    skill_b = uuid.uuid4()

    jobs = [
        # v2.0 scores
        _make_eval_job(skill_id=skill_a, composite_score=0.90, evaluator_version="v2.0"),
        _make_eval_job(skill_id=skill_b, composite_score=0.85, evaluator_version="v2.0"),
        # v1.0 scores (much lower)
        _make_eval_job(skill_id=skill_a, composite_score=0.50, evaluator_version="v1.0"),
        _make_eval_job(skill_id=skill_b, composite_score=0.45, evaluator_version="v1.0"),
    ]

    repo = AsyncMock()
    repo.get_recent_completed_jobs_all.return_value = jobs

    detector = DriftDetector(repo, model_drift_threshold=0.10)
    result = await detector.check_model_drift("v2.0", sample_size=20)

    assert result is not None
    assert isinstance(result, ModelDriftReport)
    assert result.exceeds_threshold is True
    assert result.sample_size == 2
    # MAD = (|0.90-0.50| + |0.85-0.45|) / 2 = (0.40 + 0.40) / 2 = 0.40
    assert abs(result.mean_absolute_deviation - 0.40) < 1e-9


@pytest.mark.asyncio
async def test_model_drift_single_version_returns_none():
    """When all jobs use the same version, no model drift is possible."""
    skill_id = uuid.uuid4()
    jobs = [
        _make_eval_job(skill_id=skill_id, composite_score=0.80, evaluator_version="v1.0"),
        _make_eval_job(skill_id=skill_id, composite_score=0.75, evaluator_version="v1.0"),
    ]

    repo = AsyncMock()
    repo.get_recent_completed_jobs_all.return_value = jobs

    detector = DriftDetector(repo, model_drift_threshold=0.10)
    result = await detector.check_model_drift("v1.0", sample_size=20)

    assert result is None
