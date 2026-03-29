"""Repository for source artifact provenance records."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    import asyncpg

from loom.models.provenance import ArtifactFile, SourceArtifact


def _row_to_source_artifact(row: asyncpg.Record) -> SourceArtifact:
    d = dict(row)
    for key in ("raw_metadata", "ingest_notes"):
        if isinstance(d.get(key), str):
            d[key] = json.loads(d[key])
    return SourceArtifact(**d)


def _row_to_artifact_file(row: asyncpg.Record) -> ArtifactFile:
    return ArtifactFile(**dict(row))


class SourceArtifactRepo:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def create(
        self,
        *,
        entity_kind: str,
        source_type: str,
        source_uri: str,
        artifact_hash: str,
        source_ref: str | None = None,
        raw_metadata: dict[str, object] | None = None,
        ingest_notes: dict[str, object] | None = None,
    ) -> SourceArtifact:
        row = await self._conn.fetchrow(
            """
            INSERT INTO source_artifacts (
                entity_kind, source_type, source_uri, source_ref, artifact_hash,
                raw_metadata, ingest_notes
            ) VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7::jsonb)
            RETURNING *
            """,
            entity_kind,
            source_type,
            source_uri,
            source_ref,
            artifact_hash,
            json.dumps(raw_metadata or {}),
            json.dumps(ingest_notes or {}),
        )
        return _row_to_source_artifact(row)

    async def list(self, limit: int = 50, offset: int = 0) -> list[SourceArtifact]:
        rows = await self._conn.fetch(
            """
            SELECT *
            FROM source_artifacts
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit,
            offset,
        )
        return [_row_to_source_artifact(row) for row in rows]

    async def get(self, artifact_id: UUID) -> SourceArtifact | None:
        row = await self._conn.fetchrow("SELECT * FROM source_artifacts WHERE id = $1", artifact_id)
        if row is None:
            return None
        return _row_to_source_artifact(row)

    async def get_files(self, artifact_id: UUID) -> Sequence[ArtifactFile]:
        rows = await self._conn.fetch(
            """
            SELECT artifact_id, path, kind, sha256, size_bytes, language, is_entrypoint, content_ref
            FROM artifact_files
            WHERE artifact_id = $1
            ORDER BY path ASC
            """,
            artifact_id,
        )
        return [_row_to_artifact_file(row) for row in rows]
