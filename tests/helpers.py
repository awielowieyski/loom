"""Shared test helpers and factory functions."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock

from loom.models.common import (
    CostProfile,
    DependencyDeclaration,
    EvalDimension,
    EvalScenario,
    EvalSpec,
    TrustTier,
)
from loom.models.eval import DimensionResult
from loom.models.skill import Skill


def make_test_skill(**overrides: Any) -> Skill:
    """Create a well-formed Skill for testing.

    All fields have sensible defaults; pass keyword overrides to customise.
    """
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "slug": "test-skill",
        "name": "Test Skill",
        "description": "A well-formed skill for testing.",
        "content": (
            "# Step 1: Setup\n\n"
            "Configure the environment with the required dependencies.\n\n"
            "# Step 2: Execute\n\n"
            "Run the main task using the provided context.\n\n"
            "```python\nprint('hello world')\n```\n\n"
            "# Step 3: Verify\n\n"
            "Check that the output matches the expected results.\n"
        ),
        "category_id": uuid.uuid4(),
        "tags": ["test"],
        "scope": "community",
        "version": "1.0.0",
        "author_id": uuid.uuid4(),
        "trust_tier": TrustTier.EXPERIMENTAL,
        "cost_profile": CostProfile.FREE,
        "cost_drivers": [],
        "estimated_duration": "fast",
        "dependencies": DependencyDeclaration(),
        "eval_spec": EvalSpec(
            scenarios=[
                EvalScenario(
                    description="basic test",
                    input_context="test context",
                    success_criteria="should pass",
                )
            ]
        ),
    }
    defaults.update(overrides)
    return Skill(**defaults)


def make_mock_llm_evaluator(
    *,
    score: float = 0.85,
    evidence: list[str] | None = None,
    injection_detected: bool = False,
    confidence: float = 0.90,
) -> AsyncMock:
    """Create a mock LLM evaluator returning valid DimensionResult objects."""
    if evidence is None:
        evidence = ["Good"]

    async def _evaluate_all(fragments: Any, n_runs: int = 3) -> dict[str, list[DimensionResult]]:
        results: dict[str, list[DimensionResult]] = {}
        for dim in EvalDimension:
            dim_results: list[DimensionResult] = []
            for _ in range(n_runs):
                dim_results.append(
                    DimensionResult(
                        dimension=dim,
                        score=score,
                        evidence=list(evidence),
                        injection_detected=injection_detected,
                        confidence=confidence,
                    )
                )
            results[dim.value] = dim_results
        return results

    mock = AsyncMock()
    mock.evaluate_all = AsyncMock(side_effect=_evaluate_all)
    return mock
