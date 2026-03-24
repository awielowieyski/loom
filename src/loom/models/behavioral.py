"""Domain models for M4 behavioral and comparative evaluation."""

import uuid as uuid_mod
from datetime import datetime

from pydantic import BaseModel, Field

from loom.models.common import AmendmentClassification


class RunnerOutput(BaseModel):
    """Structured output from the behavioral runner LLM."""

    actions_taken: list[str] = Field(default_factory=list)
    output: str = ""
    artifacts: list[str] = Field(default_factory=list)
    notes: str | None = None


class JudgeScore(BaseModel):
    """Structured scoring from the behavioral judge LLM."""

    outcome_quality: float = Field(ge=0.0, le=1.0)
    completeness: float = Field(ge=0.0, le=1.0)
    efficiency: float = Field(ge=0.0, le=1.0)
    evidence: str = ""
    confidence: float = Field(ge=0.0, le=1.0)
    injection_detected: bool = False


class BehavioralRunResult(BaseModel):
    """Database record for a single behavioral evaluation run."""

    id: uuid_mod.UUID
    eval_job_id: uuid_mod.UUID
    scenario_index: int
    run_index: int
    runner_output: RunnerOutput
    judge_score: float
    judge_evidence: JudgeScore
    judge_confidence: float
    injection_detected: bool = False
    runner_model_id: str = ""
    judge_model_id: str = ""
    runner_latency_ms: int | None = None
    judge_latency_ms: int | None = None
    created_at: datetime | None = None


class ComparativeAxisScores(BaseModel):
    """Per-axis scores for comparative evaluation."""

    outcome_quality: float = 0.0
    completeness: float = 0.0
    efficiency: float = 0.0
    safety: float = 0.0


class ComparativeResult(BaseModel):
    """Database record for a comparative evaluation result."""

    id: uuid_mod.UUID
    skill_a_id: uuid_mod.UUID
    skill_a_version: str
    skill_b_id: uuid_mod.UUID
    skill_b_version: str
    scenario_index: int
    winner: str  # "a", "b", "tie"
    score_a: ComparativeAxisScores
    score_b: ComparativeAxisScores
    preference_confidence: float
    reasoning: str
    classification: AmendmentClassification | None = None
    judge_model_id: str = ""
    created_at: datetime | None = None


class SkillRanking(BaseModel):
    """Database record for a skill's Elo-style ranking."""

    id: uuid_mod.UUID
    skill_id: uuid_mod.UUID
    category_id: uuid_mod.UUID
    rating: float = 1200.0
    matches_played: int = 0
    wins: int = 0
    losses: int = 0
    ties: int = 0
    last_match_at: datetime | None = None
    updated_at: datetime | None = None


class PendingBehavioralRun(BaseModel):
    """In-memory run data collected during inference, before DB persistence."""

    scenario_index: int
    run_index: int
    runner_output: RunnerOutput
    judge_score: float
    judge_evidence: JudgeScore
    judge_confidence: float
    injection_detected: bool = False
    runner_model_id: str = ""
    judge_model_id: str = ""
    runner_latency_ms: int | None = None
    judge_latency_ms: int | None = None


class BehavioralEvalResult(BaseModel):
    """Aggregated result from behavioral evaluation of a skill."""

    behavioral_score: float
    run_count: int
    scenario_count: int
    variance: float
    per_run: list[BehavioralRunResult] = Field(default_factory=list)
    pending_runs: list[PendingBehavioralRun] = Field(default_factory=list)


class ComparisonSummary(BaseModel):
    """Summary of comparative evaluation across scenarios."""

    skill_a_id: uuid_mod.UUID
    skill_b_id: uuid_mod.UUID
    per_scenario: list[ComparativeResult] = Field(default_factory=list)
    overall_winner: str = "tie"
    win_count_a: int = 0
    win_count_b: int = 0
    tie_count: int = 0


class AmendmentTriageResult(BaseModel):
    """Result of triaging an amendment against the original skill."""

    classification: AmendmentClassification
    semantic_similarity: float
    comparison: ComparisonSummary | None = None
    evidence: str = ""


class BreakingChangeReport(BaseModel):
    """Report of a skill change breaking a capability."""

    capability_slug: str
    capability_name: str
    step_index: int
    old_score: float
    new_score: float
    score_delta: float
    degraded_scenarios: list[int] = Field(default_factory=list)
