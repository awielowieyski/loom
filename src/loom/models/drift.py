"""Domain models for M4 model drift detection."""

import uuid as uuid_mod

from pydantic import BaseModel, Field


class DriftReport(BaseModel):
    """Per-skill drift detection result."""

    skill_id: uuid_mod.UUID
    old_score: float
    new_score: float
    delta: float
    exceeds_threshold: bool


class ModelDriftReport(BaseModel):
    """Aggregated drift report across a model swap."""

    old_model: str
    new_model: str
    mean_absolute_deviation: float
    exceeds_threshold: bool
    sample_size: int
    per_skill_deltas: list[DriftReport] = Field(default_factory=list)
