"""Capability domain models."""

import uuid as uuid_mod
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from loom.models.common import (
    CostProfile,
    DependencyDeclaration,
    EstimatedDuration,
    EvalSpec,
    Scope,
    TrustTier,
)


class CapabilityStep(BaseModel):
    """A single step in a capability's execution plan."""

    skill_ref: str  # URI: "loom://slug" or "corp://slug"
    role: str  # Human-readable purpose of this step
    inputs: dict[str, str] = {}
    outputs: dict[str, str] = {}
    required: bool = True
    data_classification: str = "internal"  # "internal" | "external" | "confidential"

    @field_validator("skill_ref")
    @classmethod
    def validate_uri_prefix(cls, v: str) -> str:
        if "://" not in v:
            raise ValueError(
                f"skill_ref must include a URI scheme prefix (e.g. 'loom://slug'), got: {v!r}"
            )
        return v


class DataFlowEdge(BaseModel):
    """Declared data flow between steps."""

    from_step: str
    to_step: str
    classification: str  # "internal" | "external" | "confidential"


class CapabilityCreate(BaseModel):
    slug: str
    name: str
    description: str
    category_slug: str
    version: str
    tags: list[str] = []
    scope: Scope = Scope.COMMUNITY
    trust_tier: TrustTier = TrustTier.EXPERIMENTAL
    steps: list[CapabilityStep]
    preconditions: list[str] = []
    expected_outcome: str = ""
    data_flow: list[DataFlowEdge] = []
    dependencies: DependencyDeclaration = DependencyDeclaration()
    cost_profile: CostProfile = CostProfile.FREE
    cost_drivers: list[str] = []
    estimated_duration: EstimatedDuration | str = EstimatedDuration.SLOW
    eval_spec: EvalSpec = EvalSpec()
    extends: str | None = None


class Capability(BaseModel):
    id: uuid_mod.UUID
    slug: str
    name: str
    description: str
    category_id: uuid_mod.UUID
    tags: list[str]
    scope: str
    version: str
    author_id: uuid_mod.UUID
    trust_tier: TrustTier
    steps: list[CapabilityStep]
    preconditions: list[str]
    expected_outcome: str
    data_flow: list[DataFlowEdge]
    dependencies: DependencyDeclaration = DependencyDeclaration()
    cost_profile: CostProfile
    cost_drivers: list[str]
    estimated_duration: str
    eval_spec: EvalSpec = EvalSpec()
    extends: str | None = None
    embedding: list[float] | None = Field(default=None, exclude=True)
    eval_status: str | None = None
    composite_score: float | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_summary(self) -> "CapabilitySummary":
        return CapabilitySummary(
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
            step_count=len(self.steps),
        )


class CapabilitySummary(BaseModel):
    """Lightweight capability representation for search results."""

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
    step_count: int


class CapabilityUpdate(BaseModel):
    steps: list[CapabilityStep] | None = None
    description: str | None = None
    version: str  # required — must be new version
    tags: list[str] | None = None
    preconditions: list[str] | None = None
    expected_outcome: str | None = None
    data_flow: list[DataFlowEdge] | None = None
    dependencies: DependencyDeclaration | None = None
    cost_profile: CostProfile | None = None
    cost_drivers: list[str] | None = None
    estimated_duration: EstimatedDuration | str | None = None
    eval_spec: EvalSpec | None = None
    extends: str | None = None
    changelog: str | None = None


class CapabilityVersion(BaseModel):
    id: uuid_mod.UUID
    capability_id: uuid_mod.UUID
    version: str
    steps: list[CapabilityStep]
    preconditions: list[str] | None = None
    expected_outcome: str | None = None
    data_flow: list[DataFlowEdge] | None = None
    dependencies: DependencyDeclaration | None = None
    cost_profile: str | None = None
    cost_drivers: list[str] | None = None
    estimated_duration: str | None = None
    eval_spec: EvalSpec | None = None
    extends: str | None = None
    author_id: uuid_mod.UUID
    changelog: str | None = None
    created_at: datetime | None = None
