"""Tests for UsageRepo — usage reports and aggregates persistence."""

import uuid
from datetime import UTC, datetime

import asyncpg
import pytest

from loom.db.repositories.usage_repo import UsageRepo


@pytest.fixture
def usage_repo(db_conn: asyncpg.Connection) -> UsageRepo:
    return UsageRepo(db_conn)


@pytest.mark.asyncio
async def test_create_usage_report(usage_repo: UsageRepo, test_skill_id: uuid.UUID) -> None:
    report = await usage_repo.create_usage_report(
        skill_id=test_skill_id,
        skill_version="1.0.0",
        outcome="success",
        runtime_ms=150,
        context_hash="sha256:ctx123",
        failure_reason=None,
        idempotency_key=str(uuid.uuid4()),
    )
    assert report.skill_id == test_skill_id
    assert report.outcome == "success"
    assert report.runtime_ms == 150
    assert report.context_hash == "sha256:ctx123"
    assert report.failure_reason is None


@pytest.mark.asyncio
async def test_duplicate_idempotency_key_returns_original(
    usage_repo: UsageRepo, test_skill_id: uuid.UUID
) -> None:
    key = str(uuid.uuid4())
    first = await usage_repo.create_usage_report(
        skill_id=test_skill_id,
        skill_version="1.0.0",
        outcome="success",
        idempotency_key=key,
    )
    second = await usage_repo.create_usage_report(
        skill_id=test_skill_id,
        skill_version="1.0.0",
        outcome="failure",  # different outcome
        idempotency_key=key,
    )
    assert first.id == second.id
    assert second.outcome == "success"  # original preserved


@pytest.mark.asyncio
async def test_get_reports_for_skill(usage_repo: UsageRepo, test_skill_id: uuid.UUID) -> None:
    for i in range(3):
        await usage_repo.create_usage_report(
            skill_id=test_skill_id,
            skill_version="1.0.0",
            outcome="success" if i < 2 else "failure",
            idempotency_key=str(uuid.uuid4()),
        )
    reports = await usage_repo.get_reports_for_skill(test_skill_id)
    assert len(reports) == 3


@pytest.mark.asyncio
async def test_upsert_aggregate_insert_and_update(
    usage_repo: UsageRepo, test_skill_id: uuid.UUID
) -> None:
    now = datetime.now(UTC)
    agg = await usage_repo.upsert_aggregate(
        skill_id=test_skill_id,
        skill_version="1.0.0",
        window_type="7d",
        success_count=10,
        partial_count=2,
        failure_count=1,
        success_rate=0.77,
        avg_runtime_ms=120.5,
        computed_at=now,
        window_start=now,
    )
    assert agg.success_count == 10
    assert agg.window_type == "7d"

    # Upsert updates
    agg2 = await usage_repo.upsert_aggregate(
        skill_id=test_skill_id,
        skill_version="1.0.0",
        window_type="7d",
        success_count=15,
        partial_count=3,
        failure_count=2,
        success_rate=0.75,
        avg_runtime_ms=130.0,
        computed_at=now,
        window_start=now,
    )
    assert agg2.id == agg.id
    assert agg2.success_count == 15


@pytest.mark.asyncio
async def test_get_aggregates_for_skill(usage_repo: UsageRepo, test_skill_id: uuid.UUID) -> None:
    now = datetime.now(UTC)
    for wt in ["7d", "30d", "90d"]:
        await usage_repo.upsert_aggregate(
            skill_id=test_skill_id,
            skill_version="1.0.0",
            window_type=wt,
            success_count=10,
            partial_count=0,
            failure_count=0,
            success_rate=1.0,
            avg_runtime_ms=100.0,
            computed_at=now,
            window_start=now,
        )
    aggs = await usage_repo.get_aggregates_for_skill(test_skill_id)
    assert len(aggs) == 3
    window_types = {a.window_type for a in aggs}
    assert window_types == {"7d", "30d", "90d"}
