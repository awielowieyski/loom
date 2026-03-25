"""Tests for skill timeline endpoint logic."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from loom.api.routes.timeline import _build_timeline


def _utc(*args: int) -> datetime:
    return datetime(*args, tzinfo=UTC)


@pytest.fixture()
def mock_conn() -> AsyncMock:
    return AsyncMock()


class TestBuildTimeline:
    """Tests for the _build_timeline helper."""

    async def test_submitted_event(self, mock_conn: AsyncMock) -> None:
        """Skill created_at produces a 'submitted' event."""
        mock_conn.fetch = AsyncMock(return_value=[])
        skill_id = str(uuid.uuid4())
        created = _utc(2025, 1, 15, 10, 0, 0)

        events = await _build_timeline(mock_conn, skill_id, "My Skill", created)

        submitted = [e for e in events if e.event_type == "submitted"]
        assert len(submitted) == 1
        assert submitted[0].timestamp == created
        assert "My Skill" in submitted[0].detail

    async def test_eval_completed_events(self, mock_conn: AsyncMock) -> None:
        """Eval jobs produce 'eval_completed' events."""
        eval_row = {
            "id": uuid.uuid4(),
            "composite_score": 0.85,
            "completed_at": _utc(2025, 2, 1, 12, 0, 0),
        }
        # First call: eval_jobs, second: trust_audit_log, third: skill_versions
        mock_conn.fetch = AsyncMock(side_effect=[[eval_row], [], []])
        skill_id = str(uuid.uuid4())

        events = await _build_timeline(mock_conn, skill_id, "My Skill", _utc(2025, 1, 1))

        eval_events = [e for e in events if e.event_type == "eval_completed"]
        assert len(eval_events) == 1
        assert "0.85" in eval_events[0].detail

    async def test_trust_promoted_event(self, mock_conn: AsyncMock) -> None:
        """Trust audit log with upward tier change produces 'promoted' event."""
        trust_row = {
            "previous_tier": "experimental",
            "new_tier": "community",
            "reason": "Passed threshold",
            "created_at": _utc(2025, 3, 1, 8, 0, 0),
        }
        mock_conn.fetch = AsyncMock(side_effect=[[], [trust_row], []])
        skill_id = str(uuid.uuid4())

        events = await _build_timeline(mock_conn, skill_id, "My Skill", _utc(2025, 1, 1))

        promoted = [e for e in events if e.event_type == "promoted"]
        assert len(promoted) == 1
        assert "experimental" in promoted[0].detail
        assert "community" in promoted[0].detail

    async def test_trust_demoted_event(self, mock_conn: AsyncMock) -> None:
        """Trust audit log with downward tier change produces 'demoted' event."""
        trust_row = {
            "previous_tier": "community",
            "new_tier": "experimental",
            "reason": "Failed reeval",
            "created_at": _utc(2025, 3, 1, 8, 0, 0),
        }
        mock_conn.fetch = AsyncMock(side_effect=[[], [trust_row], []])
        skill_id = str(uuid.uuid4())

        events = await _build_timeline(mock_conn, skill_id, "My Skill", _utc(2025, 1, 1))

        demoted = [e for e in events if e.event_type == "demoted"]
        assert len(demoted) == 1

    async def test_chronological_ordering(self, mock_conn: AsyncMock) -> None:
        """Events are sorted chronologically (oldest first)."""
        eval_row = {
            "id": uuid.uuid4(),
            "composite_score": 0.9,
            "completed_at": _utc(2025, 2, 1),
        }
        trust_row = {
            "previous_tier": "experimental",
            "new_tier": "community",
            "reason": "Promoted",
            "created_at": _utc(2025, 3, 1),
        }
        mock_conn.fetch = AsyncMock(side_effect=[[eval_row], [trust_row], []])
        skill_id = str(uuid.uuid4())

        events = await _build_timeline(mock_conn, skill_id, "Skill", _utc(2025, 1, 1))

        assert len(events) == 3
        assert events[0].event_type == "submitted"
        assert events[1].event_type == "eval_completed"
        assert events[2].event_type == "promoted"

    async def test_no_created_at(self, mock_conn: AsyncMock) -> None:
        """If created_at is None, no submitted event is generated."""
        mock_conn.fetch = AsyncMock(return_value=[])
        events = await _build_timeline(mock_conn, str(uuid.uuid4()), "Skill", None)
        assert all(e.event_type != "submitted" for e in events)
