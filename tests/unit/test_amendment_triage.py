"""Tests for AmendmentTriagePipeline — semantic diff + behavioral diff classification."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from loom.models.behavioral import (
    AmendmentTriageResult,
    ComparativeAxisScores,
    ComparativeResult,
    ComparisonSummary,
)
from loom.models.common import AmendmentClassification, EvalScenario
from loom.services.amendment_triage import AmendmentTriagePipeline

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_skill(
    slug: str = "test-skill",
    content: str = "# Step 1\nDo something",
    version: str = "1.0.0",
) -> MagicMock:
    """Create a mock Skill."""
    skill = MagicMock()
    skill.id = uuid.uuid4()
    skill.slug = slug
    skill.content = content
    skill.version = version
    return skill


def _default_scenarios() -> list[EvalScenario]:
    return [
        EvalScenario(
            description="Sort numbers",
            input_context="A list of numbers: [3, 1, 2]",
            success_criteria="Returns sorted list",
        )
    ]


def _make_comparative_result(
    skill_a_id: uuid.UUID,
    skill_b_id: uuid.UUID,
    winner: str = "b",
    scenario_index: int = 0,
    safety_a: float = 1.0,
    safety_b: float = 1.0,
) -> ComparativeResult:
    return ComparativeResult(
        id=uuid.uuid4(),
        skill_a_id=skill_a_id,
        skill_a_version="1.0.0",
        skill_b_id=skill_b_id,
        skill_b_version="2.0.0",
        scenario_index=scenario_index,
        winner=winner,
        score_a=ComparativeAxisScores(
            outcome_quality=0.7, completeness=0.7, efficiency=0.7, safety=safety_a
        ),
        score_b=ComparativeAxisScores(
            outcome_quality=0.8, completeness=0.8, efficiency=0.8, safety=safety_b
        ),
        preference_confidence=0.85,
        reasoning="B was better",
        judge_model_id="test-judge",
    )


def _make_comparison_summary(
    skill_a_id: uuid.UUID,
    skill_b_id: uuid.UUID,
    winners: list[str],
    safety_b_values: list[float] | None = None,
) -> ComparisonSummary:
    """Build a ComparisonSummary with the given winners per scenario."""
    if safety_b_values is None:
        safety_b_values = [1.0] * len(winners)

    results = [
        _make_comparative_result(
            skill_a_id,
            skill_b_id,
            winner=w,
            scenario_index=i,
            safety_b=safety_b_values[i],
        )
        for i, w in enumerate(winners)
    ]

    win_a = sum(1 for w in winners if w == "a")
    win_b = sum(1 for w in winners if w == "b")
    tie = sum(1 for w in winners if w == "tie")

    if win_a > win_b:
        overall = "a"
    elif win_b > win_a:
        overall = "b"
    else:
        overall = "tie"

    return ComparisonSummary(
        skill_a_id=skill_a_id,
        skill_b_id=skill_b_id,
        per_scenario=results,
        overall_winner=overall,
        win_count_a=win_a,
        win_count_b=win_b,
        tie_count=tie,
    )


def _mock_embedder(old_embedding: list[float], new_embedding: list[float]) -> AsyncMock:
    """Embedder that returns different embeddings for different content."""
    embedder = AsyncMock()
    call_count = 0

    async def embed_side_effect(content: str) -> list[float]:
        nonlocal call_count
        call_count += 1
        # First call is old_skill, second is new_skill
        if call_count == 1:
            return old_embedding
        return new_embedding

    embedder.embed = AsyncMock(side_effect=embed_side_effect)
    return embedder


def _identical_embeddings() -> tuple[list[float], list[float]]:
    """Embeddings with similarity = 1.0."""
    v = [1.0, 0.0, 0.0]
    return v, v


def _high_similarity_embeddings() -> tuple[list[float], list[float]]:
    """Embeddings with similarity ~0.97 (above high threshold)."""
    return [1.0, 0.0, 0.0], [0.98, 0.2, 0.0]


def _medium_similarity_embeddings() -> tuple[list[float], list[float]]:
    """Embeddings with similarity ~0.83 (between thresholds)."""
    return [1.0, 0.0, 0.0], [0.7, 0.7, 0.0]


def _low_similarity_embeddings() -> tuple[list[float], list[float]]:
    """Embeddings with similarity ~0.45 (below low threshold)."""
    return [1.0, 0.0, 0.0], [0.0, 0.7, 0.7]


def _mock_comparative_service(
    summary: ComparisonSummary,
) -> AsyncMock:
    service = AsyncMock()
    service.compare = AsyncMock(return_value=summary)
    return service


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAmendmentTriagePipeline:
    """AmendmentTriagePipeline classification tests."""

    async def test_high_similarity_new_better_is_refinement(self) -> None:
        """High similarity (>0.95) + new >= old -> refinement."""
        old_skill = _make_skill(slug="old", content="old content")
        new_skill = _make_skill(slug="new", content="new content")

        old_emb, new_emb = _high_similarity_embeddings()
        embedder = _mock_embedder(old_emb, new_emb)

        summary = _make_comparison_summary(old_skill.id, new_skill.id, ["b"])
        comp_service = _mock_comparative_service(summary)

        pipeline = AmendmentTriagePipeline(
            embedder=embedder,
            comparative_eval=comp_service,
            semantic_threshold_high=0.95,
            semantic_threshold_low=0.70,
        )

        result = await pipeline.triage(old_skill, new_skill, _default_scenarios())

        assert isinstance(result, AmendmentTriageResult)
        assert result.classification == AmendmentClassification.REFINEMENT
        assert result.semantic_similarity > 0.95

    async def test_high_similarity_new_worse_is_regression(self) -> None:
        """High similarity (>0.95) + new < old -> regression."""
        old_skill = _make_skill(slug="old")
        new_skill = _make_skill(slug="new")

        old_emb, new_emb = _high_similarity_embeddings()
        embedder = _mock_embedder(old_emb, new_emb)

        # All scenarios won by old skill (a)
        summary = _make_comparison_summary(old_skill.id, new_skill.id, ["a", "a"])
        comp_service = _mock_comparative_service(summary)

        pipeline = AmendmentTriagePipeline(
            embedder=embedder,
            comparative_eval=comp_service,
        )

        result = await pipeline.triage(old_skill, new_skill, _default_scenarios())

        assert result.classification == AmendmentClassification.REGRESSION

    async def test_medium_similarity_new_better_is_refinement(self) -> None:
        """Medium similarity (0.7-0.95) + new >= old -> refinement."""
        old_skill = _make_skill(slug="old")
        new_skill = _make_skill(slug="new")

        old_emb, new_emb = _medium_similarity_embeddings()
        embedder = _mock_embedder(old_emb, new_emb)

        summary = _make_comparison_summary(old_skill.id, new_skill.id, ["b", "tie"])
        comp_service = _mock_comparative_service(summary)

        pipeline = AmendmentTriagePipeline(
            embedder=embedder,
            comparative_eval=comp_service,
        )

        result = await pipeline.triage(old_skill, new_skill, _default_scenarios())

        assert result.classification == AmendmentClassification.REFINEMENT
        assert 0.70 <= result.semantic_similarity <= 0.95

    async def test_medium_similarity_new_worse_on_some_is_variant(self) -> None:
        """Medium similarity (0.7-0.95) + new < old on some -> variant."""
        old_skill = _make_skill(slug="old")
        new_skill = _make_skill(slug="new")

        old_emb, new_emb = _medium_similarity_embeddings()
        embedder = _mock_embedder(old_emb, new_emb)

        # Old wins majority
        summary = _make_comparison_summary(old_skill.id, new_skill.id, ["a", "a", "b"])
        comp_service = _mock_comparative_service(summary)

        pipeline = AmendmentTriagePipeline(
            embedder=embedder,
            comparative_eval=comp_service,
        )

        result = await pipeline.triage(old_skill, new_skill, _default_scenarios())

        assert result.classification == AmendmentClassification.VARIANT

    async def test_low_similarity_is_extension(self) -> None:
        """Low similarity (<0.7) -> extension regardless of behavioral."""
        old_skill = _make_skill(slug="old")
        new_skill = _make_skill(slug="new")

        old_emb, new_emb = _low_similarity_embeddings()
        embedder = _mock_embedder(old_emb, new_emb)

        summary = _make_comparison_summary(old_skill.id, new_skill.id, ["b"])
        comp_service = _mock_comparative_service(summary)

        pipeline = AmendmentTriagePipeline(
            embedder=embedder,
            comparative_eval=comp_service,
        )

        result = await pipeline.triage(old_skill, new_skill, _default_scenarios())

        assert result.classification == AmendmentClassification.EXTENSION
        assert result.semantic_similarity < 0.70

    async def test_safety_failure_is_rejected(self) -> None:
        """Any similarity + safety failure on new skill -> rejected."""
        old_skill = _make_skill(slug="old")
        new_skill = _make_skill(slug="new")

        old_emb, new_emb = _high_similarity_embeddings()
        embedder = _mock_embedder(old_emb, new_emb)

        # New skill has a safety failure (score_b.safety < 0.30)
        summary = _make_comparison_summary(old_skill.id, new_skill.id, ["b"], safety_b_values=[0.1])
        comp_service = _mock_comparative_service(summary)

        pipeline = AmendmentTriagePipeline(
            embedder=embedder,
            comparative_eval=comp_service,
        )

        result = await pipeline.triage(old_skill, new_skill, _default_scenarios())

        assert result.classification == AmendmentClassification.REJECTED

    async def test_cosine_similarity_computed_correctly(self) -> None:
        """Embedding similarity is computed via cosine distance."""
        old_skill = _make_skill(slug="old")
        new_skill = _make_skill(slug="new")

        # Identical embeddings -> similarity 1.0
        emb = [1.0, 0.0, 0.0]
        embedder = _mock_embedder(emb, emb)

        summary = _make_comparison_summary(old_skill.id, new_skill.id, ["tie"])
        comp_service = _mock_comparative_service(summary)

        pipeline = AmendmentTriagePipeline(
            embedder=embedder,
            comparative_eval=comp_service,
        )

        result = await pipeline.triage(old_skill, new_skill, _default_scenarios())

        assert result.semantic_similarity == pytest.approx(1.0)
        assert result.classification == AmendmentClassification.REFINEMENT
