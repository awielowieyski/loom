"""Resolution domain models — the core resolve() interface."""

from pydantic import BaseModel

from loom.models.common import CostProfile, TrustTier
from loom.models.skill import Skill, SkillSummary


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


class ResolutionError(BaseModel):
    error: str
    message: str
    suggestions: list[str] | None = None
    available_at_lower_tier: list[SkillSummary] | None = None
    successor: str | None = None
