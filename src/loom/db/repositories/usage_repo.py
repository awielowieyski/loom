"""Usage report and aggregate repository with raw asyncpg SQL."""

import uuid as uuid_mod
from datetime import datetime

import asyncpg

from loom.models.usage import UsageAggregate, UsageReport

_USAGE_REPORT_COLUMNS = (
    "id, idempotency_key, skill_id, skill_version, outcome, "
    "runtime_ms, context_hash, failure_reason, created_at"
)

_USAGE_AGGREGATE_COLUMNS = (
    "id, skill_id, skill_version, window_type, success_count, "
    "partial_count, failure_count, success_rate, avg_runtime_ms, "
    "skip_count, computed_at, window_start"
)


def _row_to_usage_report(row: asyncpg.Record) -> UsageReport:
    return UsageReport(**dict(row))


def _row_to_usage_aggregate(row: asyncpg.Record) -> UsageAggregate:
    return UsageAggregate(**dict(row))


class UsageRepo:
    """Repository for usage signal persistence."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def create_usage_report(
        self,
        *,
        skill_id: uuid_mod.UUID,
        skill_version: str,
        outcome: str,
        runtime_ms: int | None = None,
        context_hash: str | None = None,
        failure_reason: str | None = None,
        idempotency_key: str,
    ) -> UsageReport:
        """Insert a usage report with idempotency. Returns existing on conflict."""
        row = await self._conn.fetchrow(
            f"""
            INSERT INTO usage_reports (
                skill_id, skill_version, outcome, runtime_ms,
                context_hash, failure_reason, idempotency_key
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (idempotency_key) DO NOTHING
            RETURNING {_USAGE_REPORT_COLUMNS}
            """,
            skill_id,
            skill_version,
            outcome,
            runtime_ms,
            context_hash,
            failure_reason,
            idempotency_key,
        )
        if row is not None:
            return _row_to_usage_report(row)
        # Duplicate — fetch existing
        row = await self._conn.fetchrow(
            f"SELECT {_USAGE_REPORT_COLUMNS} FROM usage_reports WHERE idempotency_key = $1",
            idempotency_key,
        )
        assert row is not None
        return _row_to_usage_report(row)

    async def get_reports_for_skill(
        self,
        skill_id: uuid_mod.UUID,
        since: datetime | None = None,
    ) -> list[UsageReport]:
        """Return usage reports for a skill, optionally filtered by date."""
        if since is not None:
            rows = await self._conn.fetch(
                f"""
                SELECT {_USAGE_REPORT_COLUMNS} FROM usage_reports
                WHERE skill_id = $1 AND created_at >= $2
                ORDER BY created_at DESC
                """,
                skill_id,
                since,
            )
        else:
            rows = await self._conn.fetch(
                f"""
                SELECT {_USAGE_REPORT_COLUMNS} FROM usage_reports
                WHERE skill_id = $1
                ORDER BY created_at DESC
                """,
                skill_id,
            )
        return [_row_to_usage_report(row) for row in rows]

    async def upsert_aggregate(
        self,
        *,
        skill_id: uuid_mod.UUID,
        skill_version: str,
        window_type: str,
        success_count: int,
        partial_count: int,
        failure_count: int,
        success_rate: float | None,
        avg_runtime_ms: float | None,
        skip_count: int = 0,
        computed_at: datetime,
        window_start: datetime,
    ) -> UsageAggregate:
        """Insert or update a usage aggregate for a skill/version/window."""
        row = await self._conn.fetchrow(
            f"""
            INSERT INTO usage_aggregates (
                skill_id, skill_version, window_type,
                success_count, partial_count, failure_count,
                success_rate, avg_runtime_ms, skip_count,
                computed_at, window_start
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ON CONFLICT (skill_id, skill_version, window_type) DO UPDATE SET
                success_count = EXCLUDED.success_count,
                partial_count = EXCLUDED.partial_count,
                failure_count = EXCLUDED.failure_count,
                success_rate = EXCLUDED.success_rate,
                avg_runtime_ms = EXCLUDED.avg_runtime_ms,
                skip_count = EXCLUDED.skip_count,
                computed_at = EXCLUDED.computed_at,
                window_start = EXCLUDED.window_start
            RETURNING {_USAGE_AGGREGATE_COLUMNS}
            """,
            skill_id,
            skill_version,
            window_type,
            success_count,
            partial_count,
            failure_count,
            success_rate,
            avg_runtime_ms,
            skip_count,
            computed_at,
            window_start,
        )
        return _row_to_usage_aggregate(row)

    async def get_aggregates_for_skill(
        self,
        skill_id: uuid_mod.UUID,
    ) -> list[UsageAggregate]:
        """Return all usage aggregates for a skill."""
        rows = await self._conn.fetch(
            f"""
            SELECT {_USAGE_AGGREGATE_COLUMNS} FROM usage_aggregates
            WHERE skill_id = $1
            ORDER BY window_type
            """,
            skill_id,
        )
        return [_row_to_usage_aggregate(row) for row in rows]

    async def get_skills_needing_staleness_check(
        self,
        days: int,
    ) -> list[uuid_mod.UUID]:
        """Return skill IDs with no usage reports in `days` and stale_since IS NULL."""
        rows = await self._conn.fetch(
            """
            SELECT s.id FROM skills s
            WHERE s.stale_since IS NULL
            AND NOT EXISTS (
                SELECT 1 FROM usage_reports ur
                WHERE ur.skill_id = s.id
                AND ur.created_at >= now() - ($1 || ' days')::interval
            )
            """,
            str(days),
        )
        return [row["id"] for row in rows]

    async def count_reports_in_window(
        self,
        skill_id: uuid_mod.UUID,
        since: datetime,
    ) -> dict[str, int]:
        """Count usage reports grouped by outcome for aggregation."""
        rows = await self._conn.fetch(
            """
            SELECT outcome, COUNT(*)::int AS cnt FROM usage_reports
            WHERE skill_id = $1 AND created_at >= $2
            GROUP BY outcome
            """,
            skill_id,
            since,
        )
        return {row["outcome"]: row["cnt"] for row in rows}

    async def get_distinct_skill_versions_in_window(
        self,
        since: datetime,
    ) -> list[tuple[uuid_mod.UUID, str]]:
        """Return distinct (skill_id, skill_version) pairs with reports since `since`."""
        rows = await self._conn.fetch(
            """
            SELECT DISTINCT skill_id, skill_version FROM usage_reports
            WHERE created_at >= $1
            """,
            since,
        )
        return [(row["skill_id"], row["skill_version"]) for row in rows]

    async def aggregate_reports_in_window(
        self,
        skill_id: uuid_mod.UUID,
        skill_version: str,
        since: datetime,
    ) -> dict[str, int | float | None]:
        """Return outcome counts and avg runtime for a skill/version pair in a window."""
        rows = await self._conn.fetch(
            """
            SELECT outcome, COUNT(*)::int AS cnt,
                   AVG(runtime_ms)::float AS avg_ms
            FROM usage_reports
            WHERE skill_id = $1 AND skill_version = $2 AND created_at >= $3
            GROUP BY outcome
            """,
            skill_id,
            skill_version,
            since,
        )
        result: dict[str, int | float | None] = {
            "success": 0,
            "partial": 0,
            "failure": 0,
            "avg_runtime_ms": None,
        }
        total_runtime = 0.0
        total_with_runtime = 0
        for row in rows:
            result[row["outcome"]] = row["cnt"]
            if row["avg_ms"] is not None:
                total_runtime += row["avg_ms"] * row["cnt"]
                total_with_runtime += row["cnt"]
        if total_with_runtime > 0:
            result["avg_runtime_ms"] = total_runtime / total_with_runtime
        return result

    async def get_aggregates_above_threshold(
        self,
        window_type: str,
        min_total: int,
    ) -> list[UsageAggregate]:
        """Return aggregates where total count >= min_total for a given window type."""
        rows = await self._conn.fetch(
            f"""
            SELECT {_USAGE_AGGREGATE_COLUMNS} FROM usage_aggregates
            WHERE window_type = $1
            AND (success_count + partial_count + failure_count) >= $2
            """,
            window_type,
            min_total,
        )
        return [_row_to_usage_aggregate(row) for row in rows]

    async def get_aggregate_for_skill(
        self,
        skill_id: uuid_mod.UUID,
        window_type: str,
    ) -> UsageAggregate | None:
        """Return a single aggregate for a skill/window combination."""
        row = await self._conn.fetchrow(
            f"""
            SELECT {_USAGE_AGGREGATE_COLUMNS} FROM usage_aggregates
            WHERE skill_id = $1 AND window_type = $2
            ORDER BY computed_at DESC
            LIMIT 1
            """,
            skill_id,
            window_type,
        )
        if row is None:
            return None
        return _row_to_usage_aggregate(row)
