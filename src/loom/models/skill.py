"""Skill domain models."""

import uuid as uuid_mod
from datetime import datetime

from pydantic import BaseModel

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
    dependencies: dict[str, object]
    eval_spec: dict[str, object]
    signature: str | None = None
    extends: str | None = None
    embedding: list[float] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


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
    dependencies: dict[str, object]
    eval_spec: dict[str, object]
    cost_profile: str
    cost_drivers: list[str]
    estimated_duration: str
    extends: str | None = None
    signature: str | None = None
    author_id: uuid_mod.UUID
    changelog: str | None = None
    created_at: datetime | None = None
