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
async def test_get_queue_injection_flag() -> None:
    conn = _make_conn()
    now = datetime.now(tz=UTC)
    import uuid

    conn.fetch.side_effect = [
        # injection_flag query
        [
            {
                "skill_id": uuid.uuid4(),
                "slug": "bad-skill",
                "name": "Bad Skill",
                "eval_job_id": uuid.uuid4(),
                "composite_score": 0.3,
                "completed_at": now,
                "dimension_scores": {"clarity": 0.4, "safety": 0.2},
            }
        ],
        # low_confidence query
        [],
        # recent_amendment query
        [],
    ]

    service = GovernanceService(conn)
    result = await service.get_queue()

    assert len(result) == 1
    assert result[0]["reason"] == "injection_flag"
    assert result[0]["slug"] == "bad-skill"


@pytest.mark.asyncio
async def test_get_queue_filtered_by_reason() -> None:
    conn = _make_conn()
    conn.fetch.return_value = []

    service = GovernanceService(conn)
    result = await service.get_queue(reason="low_confidence")

    assert result == []
    # Only one query should have been made (for low_confidence)
    assert conn.fetch.call_count == 1


@pytest.mark.asyncio
async def test_submit_review() -> None:
    conn = _make_conn()
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


@pytest.mark.asyncio
async def test_get_queue_with_limit_and_offset() -> None:
    conn = _make_conn()
    now = datetime.now(tz=UTC)
    import uuid

    items = [
        {
            "skill_id": uuid.uuid4(),
            "slug": f"skill-{i}",
            "name": f"Skill {i}",
            "composite_score": 0.3,
            "last_eval_at": now,
            "dimension_scores": {},
        }
        for i in range(5)
    ]
    # Only low_confidence query runs when reason is specified
    conn.fetch.return_value = items

    service = GovernanceService(conn)
    result = await service.get_queue(reason="low_confidence", limit=2, offset=1)

    assert len(result) == 2
