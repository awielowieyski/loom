"""Tests for UsageService — usage report ingestion, aggregate retrieval, deprecation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from loom.models.common import UsageOutcome
from loom.models.usage import UsageAggregate, UsageReport, UsageReportCreate, UsageStats
from loom.services.usage_service import UsageService


def _make_skill(slug: str = "test-skill", skill_id: uuid.UUID | None = None):
    """Create a minimal mock skill object."""
    skill = MagicMock()
    skill.id = skill_id or uuid.uuid4()
    skill.slug = slug
    skill.version = "1.0.0"
    return skill


def _make_usage_report(
    skill_id: uuid.UUID,
    outcome: str = "success",
    idempotency_key: str | None = None,
) -> UsageReport:
    return UsageReport(
        id=uuid.uuid4(),
        idempotency_key=idempotency_key or str(uuid.uuid4()),
        skill_id=skill_id,
        skill_version="1.0.0",
        outcome=outcome,
        created_at=datetime.now(UTC),
    )


def _make_aggregate(
    skill_id: uuid.UUID,
    window_type: str = "7d",
    success_count: int = 10,
    failure_count: int = 2,
) -> UsageAggregate:
    total = success_count + failure_count
    return UsageAggregate(
        id=uuid.uuid4(),
        skill_id=skill_id,
        skill_version="1.0.0",
        window_type=window_type,
        success_count=success_count,
        partial_count=0,
        failure_count=failure_count,
        success_rate=success_count / total if total > 0 else None,
        avg_runtime_ms=120.0,
        computed_at=datetime.now(UTC),
        window_start=datetime.now(UTC),
    )


@pytest.fixture
def skill_repo():
    repo = AsyncMock()
    return repo


@pytest.fixture
def usage_repo():
    repo = AsyncMock()
    return repo


@pytest.fixture
def service(usage_repo, skill_repo):
    return UsageService(usage_repo=usage_repo, skill_repo=skill_repo)


@pytest.mark.asyncio
async def test_report_usage_success(service, usage_repo, skill_repo):
    """Report usage with valid data succeeds."""
    skill = _make_skill()
    skill_repo.get_by_slug.return_value = skill
    expected_report = _make_usage_report(skill.id)
    usage_repo.create_usage_report.return_value = expected_report

    report_create = UsageReportCreate(
        skill_slug="test-skill",
        skill_version="1.0.0",
        outcome=UsageOutcome.SUCCESS,
        runtime_ms=150,
        idempotency_key=str(uuid.uuid4()),
    )

    result = await service.report_usage(report_create)
    assert result.skill_id == skill.id
    skill_repo.get_by_slug.assert_awaited_once_with("test-skill")
    usage_repo.create_usage_report.assert_awaited_once()
    skill_repo.increment_resolution_count.assert_awaited_once_with(skill.id)


@pytest.mark.asyncio
async def test_report_usage_nonexistent_skill_raises(service, skill_repo):
    """Report with non-existent skill_slug raises ValueError."""
    skill_repo.get_by_slug.return_value = None

    report_create = UsageReportCreate(
        skill_slug="no-such-skill",
        skill_version="1.0.0",
        outcome=UsageOutcome.SUCCESS,
        idempotency_key=str(uuid.uuid4()),
    )

    with pytest.raises(ValueError, match="Skill not found"):
        await service.report_usage(report_create)


@pytest.mark.asyncio
async def test_report_usage_duplicate_idempotency_key(service, usage_repo, skill_repo):
    """Duplicate idempotency_key returns success (idempotent via repo)."""
    skill = _make_skill()
    skill_repo.get_by_slug.return_value = skill
    idem_key = str(uuid.uuid4())
    original_report = _make_usage_report(skill.id, idempotency_key=idem_key)
    usage_repo.create_usage_report.return_value = original_report

    report_create = UsageReportCreate(
        skill_slug="test-skill",
        skill_version="1.0.0",
        outcome=UsageOutcome.SUCCESS,
        idempotency_key=idem_key,
    )

    result = await service.report_usage(report_create)
    assert result.id == original_report.id


@pytest.mark.asyncio
async def test_get_usage_stats_returns_aggregates(service, usage_repo, skill_repo):
    """Get usage stats returns aggregates for all windows."""
    skill = _make_skill()
    skill_repo.get_by_slug.return_value = skill
    aggregates = [
        _make_aggregate(skill.id, "7d"),
        _make_aggregate(skill.id, "30d"),
        _make_aggregate(skill.id, "90d"),
    ]
    usage_repo.get_aggregates_for_skill.return_value = aggregates

    stats = await service.get_usage_stats("test-skill")
    assert isinstance(stats, UsageStats)
    assert stats.slug == "test-skill"
    assert len(stats.aggregates) == 3


@pytest.mark.asyncio
async def test_deprecate_skill_sets_fields(service, skill_repo):
    """Deprecate skill sets deprecated_at and successor_slug."""
    skill = _make_skill("old-skill")
    successor = _make_skill("new-skill")
    skill_repo.get_by_slug.side_effect = lambda slug: {
        "old-skill": skill,
        "new-skill": successor,
    }.get(slug)

    result = await service.deprecate_skill("old-skill", successor_slug="new-skill")
    assert result["deprecated"] is True
    assert result["successor_slug"] == "new-skill"
    skill_repo.mark_deprecated.assert_awaited_once_with(skill.id, "new-skill")


@pytest.mark.asyncio
async def test_deprecate_with_nonexistent_successor_raises(service, skill_repo):
    """Deprecate with non-existent successor raises ValueError."""
    skill = _make_skill("old-skill")
    skill_repo.get_by_slug.side_effect = lambda slug: (skill if slug == "old-skill" else None)

    with pytest.raises(ValueError, match="Successor skill not found"):
        await service.deprecate_skill("old-skill", successor_slug="ghost")


@pytest.mark.asyncio
async def test_check_staleness_marks_stale_skills(service, skill_repo):
    """Staleness check marks skills with 0 resolutions."""
    stale_ids = [uuid.uuid4(), uuid.uuid4()]
    skill_repo.get_stale_candidates.return_value = stale_ids

    result = await service.check_staleness(staleness_window_days=90)
    assert len(result) == 2
    assert skill_repo.mark_stale.await_count == 2
