"""Provenance and source-artifact domain models."""

import uuid as uuid_mod
from datetime import datetime

from pydantic import BaseModel, Field


class SourceArtifact(BaseModel):
    id: uuid_mod.UUID
    entity_kind: str
    source_type: str
    source_uri: str
    source_ref: str | None = None
    artifact_hash: str
    raw_metadata: dict[str, object] = Field(default_factory=dict)
    ingest_notes: dict[str, object] = Field(default_factory=dict)
    created_at: datetime | None = None


class ArtifactFile(BaseModel):
    artifact_id: uuid_mod.UUID
    path: str
    kind: str
    sha256: str
    size_bytes: int
    language: str | None = None
    is_entrypoint: bool = False
    content_ref: str | None = None


class ArtifactAdaptation(BaseModel):
    id: uuid_mod.UUID
    artifact_id: uuid_mod.UUID
    target_kind: str
    target_id: uuid_mod.UUID
    adaptation_type: str
    rationale: str
    diff_summary: dict[str, object] = Field(default_factory=dict)
    created_at: datetime | None = None
