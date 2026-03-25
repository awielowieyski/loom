"""Repository for ingestion provenance tracking."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import uuid as uuid_mod

    import asyncpg

from loom.models.ingestion import IngestionSource


class IngestionRepo:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def find_by_content_hash(self, content_hash: str) -> IngestionSource | None:
        row = await self._conn.fetchrow(
            "SELECT * FROM ingestion_sources WHERE content_hash = $1",
            content_hash,
        )
        if row is None:
            return None
        return _row_to_model(row)

    async def create(
        self,
        *,
        source_type: str,
        source_uri: str,
        content_hash: str,
        skill_id: uuid_mod.UUID | None = None,
        skill_version: str | None = None,
        raw_metadata: dict[str, object] | None = None,
    ) -> IngestionSource:
        row = await self._conn.fetchrow(
            """
            INSERT INTO ingestion_sources
                (source_type, source_uri, content_hash,
                 skill_id, skill_version, raw_metadata)
            VALUES ($1, $2, $3, $4, $5, $6::jsonb)
            RETURNING *
            """,
            source_type,
            source_uri,
            content_hash,
            skill_id,
            skill_version,
            json.dumps(raw_metadata or {}),
        )
        return _row_to_model(row)


def _row_to_model(row: asyncpg.Record) -> IngestionSource:
    return IngestionSource(
        id=row["id"],
        source_type=row["source_type"],
        source_uri=row["source_uri"],
        content_hash=row["content_hash"],
        skill_id=row["skill_id"],
        skill_version=row["skill_version"],
        ingested_at=row["ingested_at"],
        raw_metadata=row["raw_metadata"] if row["raw_metadata"] else {},
    )
