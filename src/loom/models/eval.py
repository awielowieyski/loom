"""Domain models for the M2 evaluation pipeline."""

import uuid as uuid_mod
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from loom.models.common import EvalDimension, EvalStatus, TriggerType

# --- Pipeline result models ---


class InjectionIndicator(BaseModel):
    """A detected injection pattern in skill content."""

    line: int
    pattern: str
    matched_text: str


class StructuralReport(BaseModel):
    """Result of Phase 1 static analysis."""

    passed: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    injection_indicators: list[InjectionIndicator] = Field(default_factory=list)
    complexity_score: float = 0.0
    content_hash: str = ""


class CodeBlock(BaseModel):
    """An extracted fenced code block from skill content."""

    language: str
    code: str
    line_start: int


class IsolatedFragments(BaseModel):
    """Decomposed skill content for Phase 3 isolated LLM evaluation."""

    content_hash: str
    metadata: dict[str, Any]
    step_outline: list[str]
    full_body: str
    code_blocks: list[CodeBlock] = Field(default_factory=list)
    eval_scenarios: list[dict[str, Any]] = Field(default_factory=list)
    injection_indicators: list[InjectionIndicator] = Field(default_factory=list)


class DimensionResult(BaseModel):
    """Result of a single LLM evaluation run for one dimension."""

    dimension: EvalDimension
    score: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    injection_detected: bool = False
    injection_detail: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    prompt_variant: str = ""
    model_id: str = ""


class SandboxResult(BaseModel):
    """Result of Phase 4 sandboxed execution."""

    passed: bool
    scenarios_run: int = 0
    scenarios_passed: int = 0
    errors: list[str] = Field(default_factory=list)
    lint_warnings: list[str] = Field(default_factory=list)
    duration_ms: int = 0


class EvalResult(BaseModel):
    """Aggregated result from the full evaluation pipeline."""

    passed: bool
    composite_score: float = 0.0
    dimension_scores: dict[str, float] = Field(default_factory=dict)
    dimension_confidence: dict[str, float] = Field(default_factory=dict)
    overall_confidence: float = 0.0
    injection_flagged: bool = False
    sandbox_passed: bool | None = None
    content_hash: str = ""
    evaluator_version: str = ""


class ComparisonResult(BaseModel):
    """Result of comparing an amendment against the original."""

    verdict: str
    original_scores: dict[str, float] = Field(default_factory=dict)
    amendment_scores: dict[str, float] = Field(default_factory=dict)
    dimension_deltas: dict[str, float] = Field(default_factory=dict)
    auto_merge: bool = False
    reason: str = ""


# --- Database record models ---


class EvalJob(BaseModel):
    """Database record for an evaluation job."""

    id: uuid_mod.UUID
    skill_id: uuid_mod.UUID
    skill_version: str
    content_hash: str
    trigger_type: TriggerType
    status: EvalStatus = EvalStatus.PENDING
    structural_report: dict[str, Any] | None = None
    composite_score: float | None = None
    dimension_scores: dict[str, float] | None = None
    dimension_confidence: dict[str, float] | None = None
    injection_flagged: bool = False
    sandbox_passed: bool | None = None
    overall_confidence: float | None = None
    evaluator_version: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None


class EvalDimensionRun(BaseModel):
    """Database record for a single dimension evaluation run."""

    id: uuid_mod.UUID
    eval_job_id: uuid_mod.UUID
    dimension: EvalDimension
    run_index: int
    score: float
    evidence: list[str] = Field(default_factory=list)
    injection_detected: bool = False
    injection_detail: str | None = None
    confidence: float = 0.0
    prompt_variant: str = ""
    model_id: str = ""
    latency_ms: int | None = None
    created_at: datetime | None = None


class TrustAuditEntry(BaseModel):
    """Database record for a trust tier change."""

    id: uuid_mod.UUID
    skill_id: uuid_mod.UUID
    previous_tier: str
    new_tier: str
    reason: str
    eval_job_id: uuid_mod.UUID | None = None
    promoted_by: uuid_mod.UUID | None = None
    created_at: datetime | None = None
