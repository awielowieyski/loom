"""Tests for GovernanceService."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from loom.services.governance_service import GovernanceService


def _make_conn() -> AsyncMock:
    return AsyncMock()


@pytest.mark.asyncio
async def test_get_queue_empty() -> None:
    conn = _make_conn()
    conn.fetch.return_value = []

    service = GovernanceService(conn)
    result = await service.get_queue()

    assert result == []


@pytest.mark.asyncio
async def test_get_queue_maps_lifecycle_stage_and_reason() -> None:
    conn = _make_conn()
    now = datetime.now(tz=UTC)
    conn.fetch.return_value = [
        {
            "skill_id": "00000000-0000-0000-0000-000000000123",
            "slug": "draft-skill",
            "name": "Draft Skill",
            "display_name": "Canonical Draft Skill",
            "lifecycle_state": "canonicalizing",
            "trust_tier": "unvetted",
            "provenance_summary": {"source_uri": "https://example.com/skill"},
            "authorship_status": "loom_amended",
            "canonicalization_level": "substantive",
            "current_version_id": None,
            "published_version_id": None,
            "composite_score": None,
            "eval_status": "running",
            "updated_at": now,
            "created_at": now,
            "dimension_scores": None,
            "injection_flagged": False,
            "changelog": None,
        }
    ]

    service = GovernanceService(conn)
    result = await service.get_queue(stage="canonicalization")

    assert len(result) == 1
    assert result[0]["stage"] == "canonicalization"
    assert result[0]["name"] == "Canonical Draft Skill"
    assert result[0]["reason"] == "low_confidence"
    assert result[0]["authorship_status"] == "loom_amended"


@pytest.mark.asyncio
async def test_get_queue_filtered_by_stage() -> None:
    conn = _make_conn()
    now = datetime.now(tz=UTC)
    conn.fetch.return_value = [
        {
            "skill_id": "00000000-0000-0000-0000-000000000124",
            "slug": "quarantined-skill",
            "name": "Quarantined Skill",
            "display_name": None,
            "lifecycle_state": "quarantined",
            "trust_tier": "unvetted",
            "provenance_summary": {},
            "authorship_status": None,
            "canonicalization_level": None,
            "current_version_id": None,
            "published_version_id": None,
            "composite_score": None,
            "eval_status": None,
            "updated_at": now,
            "created_at": now,
            "dimension_scores": None,
            "injection_flagged": False,
            "changelog": None,
        },
        {
            "skill_id": "00000000-0000-0000-0000-000000000125",
            "slug": "published-skill",
            "name": "Published Skill",
            "display_name": None,
            "lifecycle_state": "published",
            "trust_tier": "experimental",
            "provenance_summary": {},
            "authorship_status": "author_owned",
            "canonicalization_level": "none",
            "current_version_id": None,
            "published_version_id": None,
            "composite_score": 0.8,
            "eval_status": "completed",
            "updated_at": now,
            "created_at": now,
            "dimension_scores": {},
            "injection_flagged": False,
            "changelog": "Published",
        },
    ]

    service = GovernanceService(conn)
    result = await service.get_queue(stage="quarantine")

    assert len(result) == 1
    assert result[0]["slug"] == "quarantined-skill"


@pytest.mark.asyncio
async def test_submit_review() -> None:
    conn = _make_conn()
    conn.fetchrow.return_value = {
        "id": "skill-id",
        "trust_tier": "unvetted",
        "lifecycle_state": "evaluating",
    }
    conn.execute.return_value = None

    service = GovernanceService(conn)
    result = await service.submit_review(
        queue_item_id="test-item-id",
        decision="approve",
        note="Looks good",
    )

    assert result["success"] is True
    assert result["decision"] == "approve"
    assert result["note"] == "Looks good"
    assert result["lifecycle_state"] == "published"
    assert result["trust_tier"] == "experimental"


@pytest.mark.asyncio
async def test_submit_review_request_changes_moves_to_review_without_trust_audit() -> None:
    conn = _make_conn()
    conn.fetchrow.return_value = {
        "id": "skill-id",
        "trust_tier": "experimental",
        "lifecycle_state": "canonicalizing",
    }
    conn.execute.return_value = None

    service = GovernanceService(conn)
    result = await service.submit_review(
        queue_item_id="skill-id",
        decision="request_changes",
        note="Needs revision",
    )

    assert result["success"] is True
    assert result["lifecycle_state"] == "review"
    assert result["trust_tier"] == "experimental"
    assert conn.execute.await_count == 2
