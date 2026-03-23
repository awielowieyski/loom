"""Domain models for the M2 evaluation pipeline."""

from typing import Any

from pydantic import BaseModel, Field


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
