"""Repository for pipeline rerun requests."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    import asyncpg


from loom.models.pipeline import PipelineRunRequest


def _row_to_request(row: asyncpg.Record) -> PipelineRunRequest:
    data = dict(row)
    if isinstance(data.get("result_summary"), str):
        data["result_summary"] = json.loads(data["result_summary"])
    return PipelineRunRequest(**data)


class PipelineRunRepo:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def create(
        self,
        *,
        skill_id: UUID | None,
        artifact_id: UUID | None,
        request_mode: str,
        requested_via: str,
        note: str | None = None,
        status: str = "pending",
    ) -> PipelineRunRequest:
        row = await self._conn.fetchrow(
            """
            INSERT INTO pipeline_run_requests (
                skill_id, artifact_id, request_mode, status, requested_via, note,
                started_at, completed_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING *
            """,
            skill_id,
            artifact_id,
            request_mode,
            status,
            requested_via,
            note,
            datetime.now(UTC) if status == "running" else None,
            datetime.now(UTC) if status in {"completed", "failed"} else None,
        )
        assert row is not None
        return _row_to_request(row)

    async def update_status(
        self,
        request_id: UUID,
        *,
        status: str,
        result_summary: dict[str, object] | None = None,
    ) -> PipelineRunRequest | None:
        row = await self._conn.fetchrow(
            """
            UPDATE pipeline_run_requests
            SET status = $2,
                result_summary = COALESCE($3::jsonb, result_summary),
                started_at = COALESCE(started_at, now()),
                completed_at = CASE
                    WHEN $2 IN ('completed', 'failed') THEN now()
                    ELSE completed_at
                END
            WHERE id = $1
            RETURNING *
            """,
            request_id,
            status,
            json.dumps(result_summary) if result_summary is not None else None,
        )
        return _row_to_request(row) if row is not None else None

    async def list_for_skill(
        self,
        skill_id: UUID,
        limit: int = 10,
    ) -> list[PipelineRunRequest]:
        rows = await self._conn.fetch(
            """
            SELECT *
            FROM pipeline_run_requests
            WHERE skill_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            skill_id,
            limit,
        )
        return [_row_to_request(row) for row in rows]
