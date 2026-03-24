"""ActivityFeedService: unified activity stream from multiple tables."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    import asyncpg

from loom.models.activity import ActivityEvent


class ActivityFeedService:
    """Aggregates events from skills, capabilities, trust_audit_log, and eval_jobs."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def get_feed(
        self,
        limit: int = 20,
        since: datetime | None = None,
    ) -> list[ActivityEvent]:
        """Return a unified, chronologically sorted event list (newest first)."""
        events: list[ActivityEvent] = []

        events.extend(await self._skill_events(since))
        events.extend(await self._capability_events(since))
        events.extend(await self._trust_events(since))
        events.extend(await self._eval_events(since))

        # Sort newest first, then limit
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]

    async def _skill_events(self, since: datetime | None) -> list[ActivityEvent]:
        where = "WHERE created_at > $1" if since else ""
        params: list[object] = [since] if since else []
        sql = (
            f"SELECT id, slug, name, created_at FROM skills {where}"
            " ORDER BY created_at DESC LIMIT 100"
        )
        rows = await self._conn.fetch(sql, *params)
        return [
            ActivityEvent(
                id=str(row["id"]),
                event_type="skill_submitted",
                timestamp=row["created_at"],
                slug=row["slug"],
                name=row["name"],
                detail=f"Skill '{row['name']}' submitted",
            )
            for row in rows
        ]

    async def _capability_events(self, since: datetime | None) -> list[ActivityEvent]:
        where = "WHERE created_at > $1" if since else ""
        params: list[object] = [since] if since else []
        sql = (
            f"SELECT id, slug, name, created_at FROM capabilities {where}"
            " ORDER BY created_at DESC LIMIT 100"
        )
        rows = await self._conn.fetch(sql, *params)
        return [
            ActivityEvent(
                id=str(row["id"]),
                event_type="capability_submitted",
                timestamp=row["created_at"],
                slug=row["slug"],
                name=row["name"],
                detail=f"Capability '{row['name']}' submitted",
            )
            for row in rows
        ]

    async def _trust_events(self, since: datetime | None) -> list[ActivityEvent]:
        where = "WHERE t.created_at > $1" if since else ""
        params: list[object] = [since] if since else []
        sql = f"""
            SELECT t.id, t.previous_tier, t.new_tier, t.reason, t.created_at,
                   s.slug, s.name
            FROM trust_audit_log t
            JOIN skills s ON s.id = t.skill_id
            {where}
            ORDER BY t.created_at DESC LIMIT 100
        """
        rows = await self._conn.fetch(sql, *params)
        events: list[ActivityEvent] = []
        for row in rows:
            prev_rank = _trust_rank(row["previous_tier"])
            new_rank = _trust_rank(row["new_tier"])
            event_type = "trust_promoted" if new_rank > prev_rank else "trust_demoted"
            events.append(
                ActivityEvent(
                    id=str(row["id"]),
                    event_type=event_type,
                    timestamp=row["created_at"],
                    slug=row["slug"],
                    name=row["name"],
                    detail=(
                        f"Trust tier changed: {row['previous_tier']}"
                        f" -> {row['new_tier']} ({row['reason']})"
                    ),
                    previous_value=row["previous_tier"],
                    new_value=row["new_tier"],
                )
            )
        return events

    async def _eval_events(self, since: datetime | None) -> list[ActivityEvent]:
        where_clause = "WHERE e.status = 'completed'"
        params: list[object] = []
        if since:
            where_clause += " AND e.completed_at > $1"
            params.append(since)
        sql = f"""
            SELECT e.id, e.composite_score, e.completed_at,
                   s.slug, s.name
            FROM eval_jobs e
            JOIN skills s ON s.id = e.skill_id
            {where_clause}
            ORDER BY e.completed_at DESC LIMIT 100
        """
        rows = await self._conn.fetch(sql, *params)
        return [
            ActivityEvent(
                id=str(row["id"]),
                event_type="eval_completed",
                timestamp=row["completed_at"],
                slug=row["slug"],
                name=row["name"],
                detail=(
                    f"Evaluation completed for '{row['name']}'"
                    f" (score: {row['composite_score']})"
                ),
            )
            for row in rows
        ]


_TRUST_RANK = {"experimental": 0, "community": 1, "verified": 2}


def _trust_rank(tier: str) -> int:
    return _TRUST_RANK.get(tier, 0)
