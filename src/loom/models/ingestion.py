"""Ingestion provenance models."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    import uuid as uuid_mod
    from datetime import datetime


class IngestionSource(BaseModel):
    """Record of a skill ingested from an external source."""

    id: uuid_mod.UUID
    source_type: str
    source_uri: str
    content_hash: str
    skill_id: uuid_mod.UUID | None = None
    skill_version: str | None = None
    ingested_at: datetime
    raw_metadata: dict[str, object] = Field(default_factory=dict)
