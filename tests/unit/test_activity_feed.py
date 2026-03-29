"""Tests for ActivityFeedService."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from loom.services.activity_feed import ActivityFeedService, _trust_rank


def _make_skill_row(
    slug: str = "test-skill",
    name: str = "Test Skill",
    created_at: datetime | None = None,
) -> dict:
    return {
        "id": uuid.uuid4(),
        "slug": slug,
        "name": name,
        "created_at": created_at or datetime.now(tz=UTC),
    }


def _make_capability_row(
    slug: str = "test-cap",
    name: str = "Test Cap",
    created_at: datetime | None = None,
) -> dict:
    return {
        "id": uuid.uuid4(),
        "slug": slug,
        "name": name,
        "created_at": created_at or datetime.now(tz=UTC),
    }


def _make_trust_row(
    slug: str = "test-skill",
    name: str = "Test Skill",
    previous_tier: str = "experimental",
    new_tier: str = "community",
    reason: str = "Passed eval",
    created_at: datetime | None = None,
) -> dict:
    return {
        "id": uuid.uuid4(),
        "slug": slug,
        "name": name,
        "previous_tier": previous_tier,
        "new_tier": new_tier,
        "reason": reason,
        "created_at": created_at or datetime.now(tz=UTC),
    }


def _make_eval_row(
    slug: str = "test-skill",
    name: str = "Test Skill",
    composite_score: float = 0.85,
    completed_at: datetime | None = None,
) -> dict:
    return {
        "id": uuid.uuid4(),
        "slug": slug,
        "name": name,
        "composite_score": composite_score,
        "completed_at": completed_at or datetime.now(tz=UTC),
    }


@pytest.fixture
def mock_conn() -> MagicMock:
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[])
    return conn


async def test_empty_feed(mock_conn: MagicMock) -> None:
    """Returns empty list when no events exist."""
    service = ActivityFeedService(mock_conn)
    events = await service.get_feed()
    assert events == []


async def test_skill_submitted_events(mock_conn: MagicMock) -> None:
    """Returns skill_submitted events from skills table."""
    rows = [_make_skill_row("my-skill", "My Skill")]
    # First call is for skills, rest return empty
    mock_conn.fetch = AsyncMock(side_effect=[rows, [], [], []])

    service = ActivityFeedService(mock_conn)
    events = await service.get_feed()

    assert len(events) == 1
    assert events[0].event_type == "skill_submitted"
    assert events[0].slug == "my-skill"


async def test_capability_submitted_events(mock_conn: MagicMock) -> None:
    """Returns capability_submitted events."""
    rows = [_make_capability_row("my-cap", "My Cap")]
    mock_conn.fetch = AsyncMock(side_effect=[[], rows, [], []])

    service = ActivityFeedService(mock_conn)
    events = await service.get_feed()

    assert len(events) == 1
    assert events[0].event_type == "capability_submitted"
    assert events[0].slug == "my-cap"


async def test_trust_promoted_events(mock_conn: MagicMock) -> None:
    """Returns trust_promoted events for tier upgrades."""
    rows = [_make_trust_row(previous_tier="experimental", new_tier="community")]
    mock_conn.fetch = AsyncMock(side_effect=[[], [], rows, []])

    service = ActivityFeedService(mock_conn)
    events = await service.get_feed()

    assert len(events) == 1
    assert events[0].event_type == "trust_promoted"
    assert events[0].previous_value == "experimental"
    assert events[0].new_value == "community"


async def test_trust_demoted_events(mock_conn: MagicMock) -> None:
    """Returns trust_demoted events for tier downgrades."""
    rows = [_make_trust_row(previous_tier="verified", new_tier="experimental")]
    mock_conn.fetch = AsyncMock(side_effect=[[], [], rows, []])

    service = ActivityFeedService(mock_conn)
    events = await service.get_feed()

    assert len(events) == 1
    assert events[0].event_type == "trust_demoted"


async def test_eval_completed_events(mock_conn: MagicMock) -> None:
    """Returns eval_completed events."""
    rows = [_make_eval_row(composite_score=0.92)]
    mock_conn.fetch = AsyncMock(side_effect=[[], [], [], rows])

    service = ActivityFeedService(mock_conn)
    events = await service.get_feed()

    assert len(events) == 1
    assert events[0].event_type == "eval_completed"
    assert "0.92" in events[0].detail


async def test_feed_sorted_newest_first(mock_conn: MagicMock) -> None:
    """Events from multiple sources are sorted newest first."""
    old_time = datetime(2024, 1, 1, tzinfo=UTC)
    new_time = datetime(2024, 6, 1, tzinfo=UTC)

    skill_rows = [_make_skill_row("old-skill", created_at=old_time)]
    cap_rows = [_make_capability_row("new-cap", created_at=new_time)]
    mock_conn.fetch = AsyncMock(side_effect=[skill_rows, cap_rows, [], []])

    service = ActivityFeedService(mock_conn)
    events = await service.get_feed()

    assert len(events) == 2
    assert events[0].slug == "new-cap"
    assert events[1].slug == "old-skill"


async def test_feed_respects_limit(mock_conn: MagicMock) -> None:
    """Feed returns at most `limit` events."""
    skill_rows = [_make_skill_row(f"skill-{i}") for i in range(10)]
    mock_conn.fetch = AsyncMock(side_effect=[skill_rows, [], [], []])

    service = ActivityFeedService(mock_conn)
    events = await service.get_feed(limit=3)

    assert len(events) == 3


async def test_feed_passes_since_parameter(mock_conn: MagicMock) -> None:
    """Feed passes since parameter to queries."""
    since = datetime(2024, 6, 1, tzinfo=UTC)
    mock_conn.fetch = AsyncMock(return_value=[])

    service = ActivityFeedService(mock_conn)
    await service.get_feed(since=since)

    # All 4 queries should have been called with the since parameter
    assert mock_conn.fetch.call_count == 4
    for call in mock_conn.fetch.call_args_list:
        args = call[0]
        # The SQL should contain WHERE clause and since as a parameter
        assert ">" in args[0] or "WHERE" in args[0]


async def test_feed_queries_only_published_rows(mock_conn: MagicMock) -> None:
    """Public feed excludes non-published drafts."""
    service = ActivityFeedService(mock_conn)
    await service.get_feed()

    assert mock_conn.fetch.call_count == 4
    for call in mock_conn.fetch.call_args_list:
        sql = call[0][0]
        assert "lifecycle_state = 'published'" in sql


def test_trust_rank_values() -> None:
    """Trust rank helper returns correct ordering."""
    assert _trust_rank("experimental") == 0
    assert _trust_rank("community") == 1
    assert _trust_rank("verified") == 2
    assert _trust_rank("unknown") == 0
