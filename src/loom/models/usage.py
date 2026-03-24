"""Domain models for M4 usage signal collection and aggregation."""

import uuid as uuid_mod
from datetime import datetime

from pydantic import BaseModel, Field

from loom.models.common import UsageOutcome, WindowType


class UsageReportCreate(BaseModel):
    """Request body for submitting a usage report."""

    skill_slug: str
    skill_version: str
    outcome: UsageOutcome
    runtime_ms: int | None = None
    context_hash: str | None = None
    failure_reason: str | None = None
    idempotency_key: str


class UsageReport(BaseModel):
    """Database record for a single usage report."""

    id: uuid_mod.UUID
    idempotency_key: str
    skill_id: uuid_mod.UUID
    skill_version: str
    outcome: UsageOutcome
    runtime_ms: int | None = None
    context_hash: str | None = None
    failure_reason: str | None = None
    created_at: datetime | None = None


class UsageAggregate(BaseModel):
    """Precomputed usage statistics for a skill over a time window."""

    id: uuid_mod.UUID
    skill_id: uuid_mod.UUID
    skill_version: str
    window_type: WindowType
    success_count: int = 0
    partial_count: int = 0
    failure_count: int = 0
    success_rate: float | None = None
    avg_runtime_ms: float | None = None
    skip_count: int = 0
    computed_at: datetime | None = None
    window_start: datetime | None = None


class UsageStats(BaseModel):
    """Convenience wrapper for API response with aggregated usage data."""

    slug: str
    aggregates: list[UsageAggregate] = Field(default_factory=list)
