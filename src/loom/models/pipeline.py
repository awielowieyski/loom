"""Pipeline rerun request models."""

import uuid as uuid_mod
from datetime import datetime

from pydantic import BaseModel, Field


class PipelineRunRequest(BaseModel):
    id: uuid_mod.UUID
    skill_id: uuid_mod.UUID | None = None
    artifact_id: uuid_mod.UUID | None = None
    request_mode: str
    status: str
    requested_via: str
    note: str | None = None
    result_summary: dict[str, object] = Field(default_factory=dict)
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
