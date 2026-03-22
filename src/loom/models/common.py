"""Shared domain types used across skills, capabilities, and resolution."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel

_TRUST_RANK: dict[str, int] = {"experimental": 0, "community": 1, "verified": 2}
_COST_RANK: dict[str, int] = {"free": 0, "low": 1, "moderate": 2, "high": 3}


class TrustTier(StrEnum):
    EXPERIMENTAL = "experimental"
    COMMUNITY = "community"
    VERIFIED = "verified"

    @property
    def rank(self) -> int:
        return _TRUST_RANK[self]

    def meets_floor(self, floor: "TrustTier") -> bool:
        return self.rank >= floor.rank


class CostProfile(StrEnum):
    FREE = "free"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"

    @property
    def rank(self) -> int:
        return _COST_RANK[self]

    def within_budget(self, budget: "CostProfile") -> bool:
        return self.rank <= budget.rank


class EstimatedDuration(StrEnum):
    FAST = "fast"
    MODERATE = "moderate"
    SLOW = "slow"


class Scope(StrEnum):
    COMMUNITY = "community"
    CORPORATE = "corporate"


class PrivacyImpact(BaseModel):
    external_data_sharing: bool = False
    input_logging: Literal["none", "anonymised", "full", "unknown"] = "unknown"
    data_retention: Literal["none", "transient", "persistent", "unknown"] = "unknown"


class TrustRequirements(BaseModel):
    data_classification: Literal["none", "internal", "confidential"] = "none"
    network_access: bool = False
    privacy_impact: PrivacyImpact = PrivacyImpact()


class MCPServerDependency(BaseModel):
    uri: str
    required: bool = True
    scopes: list[str] = []


class APIDependency(BaseModel):
    name: str
    auth_type: str = "api_key"
    scopes: list[str] = []


class DependencyDeclaration(BaseModel):
    mcp_servers: list[MCPServerDependency] = []
    apis: list[APIDependency] = []
    trust_requirements: TrustRequirements = TrustRequirements()


class EvalScenario(BaseModel):
    description: str
    input_context: str
    success_criteria: str


class QualityDimension(BaseModel):
    name: str
    description: str


class EvalSpec(BaseModel):
    scenarios: list[EvalScenario] = []
    quality_dimensions: list[QualityDimension] = []
