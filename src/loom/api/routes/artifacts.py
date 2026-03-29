"""Source artifact provenance API routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID  # noqa: TC003 — needed at runtime by FastAPI/Pydantic

import asyncpg  # noqa: TC002 — needed at runtime by FastAPI/Pydantic
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from loom.api.deps import get_conn
from loom.api.middleware import verify_api_key
from loom.db.repositories.source_artifact_repo import SourceArtifactRepo
from loom.models.provenance import ArtifactFile, SourceArtifact

router = APIRouter(prefix="/api/v1/artifacts", tags=["artifacts"])


class SourceArtifactCreate(BaseModel):
    entity_kind: str = "skill"
    source_type: str
    source_uri: str
    artifact_hash: str
    source_ref: str | None = None
    raw_metadata: dict[str, object] | None = None
    ingest_notes: dict[str, object] | None = None


class SourceArtifactDetail(BaseModel):
    artifact: SourceArtifact
    files: list[ArtifactFile]


@router.get("", response_model=list[SourceArtifact])
async def list_artifacts(
    _: Annotated[str | None, Depends(verify_api_key)],
    conn: Annotated[asyncpg.Connection, Depends(get_conn)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[SourceArtifact]:
    repo = SourceArtifactRepo(conn)
    return await repo.list(limit=limit, offset=offset)


@router.post("", response_model=SourceArtifact, status_code=status.HTTP_201_CREATED)
async def create_artifact(
    body: SourceArtifactCreate,
    _: Annotated[str | None, Depends(verify_api_key)],
    conn: Annotated[asyncpg.Connection, Depends(get_conn)],
) -> SourceArtifact:
    repo = SourceArtifactRepo(conn)
    return await repo.create(
        entity_kind=body.entity_kind,
        source_type=body.source_type,
        source_uri=body.source_uri,
        source_ref=body.source_ref,
        artifact_hash=body.artifact_hash,
        raw_metadata=body.raw_metadata,
        ingest_notes=body.ingest_notes,
    )


@router.get("/{artifact_id}", response_model=SourceArtifactDetail)
async def get_artifact(
    artifact_id: UUID,
    _: Annotated[str | None, Depends(verify_api_key)],
    conn: Annotated[asyncpg.Connection, Depends(get_conn)],
) -> SourceArtifactDetail:
    repo = SourceArtifactRepo(conn)
    artifact = await repo.get(artifact_id)
    if artifact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact {artifact_id!s} not found",
        )
    files = await repo.get_files(artifact_id)
    return SourceArtifactDetail(artifact=artifact, files=files)
