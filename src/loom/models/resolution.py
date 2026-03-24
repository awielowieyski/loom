"""Resolution domain models — the core resolve() interface."""

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel

from loom.models.common import CostProfile, TrustTier
from loom.models.skill import Skill, SkillSummary

if TYPE_CHECKING:
    from loom.models.capability import Capability, DataFlowEdge


class ResolutionContext(BaseModel):
    trust_floor: TrustTier | None = None
    cost_budget: CostProfile | None = None
    latency_budget: str | None = None
    data_classification: str | None = None
    available_tools: list[str] = []
    approved_providers: list[str] = []
    runtime: str | None = None


class Alternative(BaseModel):
    skill: SkillSummary
    match_score: float
    tradeoff: str


class RejectedCandidate(BaseModel):
    skill: SkillSummary
    reason: str


class ResolvedSkill(BaseModel):
    skill: Skill
    dependencies_satisfied: list[str] = []
    dependencies_missing: list[str] = []
    alternatives: list[Alternative] = []
    rejected_candidates: list[RejectedCandidate] = []
    selection_rationale: list[str] = []


class ResolvedStep(BaseModel):
    """A step with its skill fully resolved and embedded."""

    index: int
    skill_ref: str
    role: str
    skill: Skill
    inputs: dict[str, str]
    outputs: dict[str, str]
    required: bool
    data_classification: str
    dependencies_satisfied: list[str] = []
    dependencies_missing: list[str] = []


class ResolvedCapability(BaseModel):
    """A fully resolved capability with all steps' skills embedded."""

    capability: "Capability"
    resolved_steps: list[ResolvedStep]
    effective_trust_tier: TrustTier
    trust_warnings: list[str] = []
    all_dependencies_satisfied: list[str] = []
    all_dependencies_missing: list[str] = []
    data_flow: list["DataFlowEdge"]
    alternatives: list[Alternative] = []
    selection_rationale: list[str] = []


class ResolvedResult(BaseModel):
    """Union result from resolve() — either a skill or a capability."""

    type: Literal["skill", "capability"]
    skill: ResolvedSkill | None = None
    capability: ResolvedCapability | None = None


class ResolutionError(BaseModel):
    error: str
    message: str
    suggestions: list[str] | None = None
    available_at_lower_tier: list[SkillSummary] | None = None
    successor: str | None = None


def _rebuild_forward_refs() -> None:
    """Rebuild models that use forward references to capability types."""
    from loom.models.capability import (  # noqa: PLC0415
        Capability,
        DataFlowEdge,
    )

    ResolvedCapability.model_rebuild(
        _types_namespace={
            "Capability": Capability,
            "DataFlowEdge": DataFlowEdge,
        }
    )


_rebuild_forward_refs()
