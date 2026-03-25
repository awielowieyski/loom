"""Skill domain models."""

import uuid as uuid_mod
from datetime import datetime

from pydantic import BaseModel, Field

from loom.models.common import (
    CostProfile,
    DependencyDeclaration,
    EstimatedDuration,
    EvalSpec,
    Scope,
    TrustTier,
)


class SkillCreate(BaseModel):
    slug: str
    name: str
    description: str
    content: str
    category_slug: str
    version: str
    tags: list[str] = []
    scope: Scope = Scope.COMMUNITY
    trust_tier: TrustTier = TrustTier.EXPERIMENTAL
    cost_profile: CostProfile = CostProfile.FREE
    cost_drivers: list[str] = []
    estimated_duration: EstimatedDuration | str = EstimatedDuration.FAST
    dependencies: DependencyDeclaration = DependencyDeclaration()
    eval_spec: EvalSpec = EvalSpec()
    extends: str | None = None
    source_uri: str | None = None
    license: str | None = None


class Skill(BaseModel):
    id: uuid_mod.UUID
    slug: str
    name: str
    description: str
    content: str
    category_id: uuid_mod.UUID
    tags: list[str]
    scope: str
    version: str
    author_id: uuid_mod.UUID
    trust_tier: TrustTier
    cost_profile: CostProfile
    cost_drivers: list[str]
    estimated_duration: str
    dependencies: DependencyDeclaration = DependencyDeclaration()
    eval_spec: EvalSpec = EvalSpec()
    signature: str | None = None
    extends: str | None = None
    embedding: list[float] | None = Field(default=None, exclude=True)
    eval_status: str | None = None
    composite_score: float | None = None
    latest_eval_job_id: str | None = None
    signature_key_fingerprint: str | None = None
    source_uri: str | None = None
    license: str | None = None
    # M4: living registry columns
    deprecated_at: datetime | None = None
    successor_slug: str | None = None
    stale_since: datetime | None = None
    behavioral_score: float | None = None
    last_eval_at: datetime | None = None
    resolution_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_summary(self) -> "SkillSummary":
        return SkillSummary(
            id=self.id,
            slug=self.slug,
            name=self.name,
            description=self.description,
            category_id=self.category_id,
            tags=self.tags,
            version=self.version,
            trust_tier=self.trust_tier,
            cost_profile=self.cost_profile,
            estimated_duration=self.estimated_duration,
        )


class SkillSummary(BaseModel):
    id: uuid_mod.UUID
    slug: str
    name: str
    description: str
    category_id: uuid_mod.UUID
    tags: list[str]
    version: str
    trust_tier: TrustTier
    cost_profile: CostProfile
    estimated_duration: str


class SkillUpdate(BaseModel):
    content: str | None = None
    description: str | None = None
    version: str  # required — must be new version
    tags: list[str] | None = None
    cost_profile: CostProfile | None = None
    cost_drivers: list[str] | None = None
    estimated_duration: EstimatedDuration | str | None = None
    dependencies: DependencyDeclaration | None = None
    eval_spec: EvalSpec | None = None
    extends: str | None = None
    changelog: str | None = None


class SkillVersion(BaseModel):
    id: uuid_mod.UUID
    skill_id: uuid_mod.UUID
    version: str
    content: str
    dependencies: DependencyDeclaration = DependencyDeclaration()
    eval_spec: EvalSpec = EvalSpec()
    cost_profile: str
    cost_drivers: list[str]
    estimated_duration: str
    extends: str | None = None
    signature: str | None = None
    author_id: uuid_mod.UUID
    changelog: str | None = None
    created_at: datetime | None = None
