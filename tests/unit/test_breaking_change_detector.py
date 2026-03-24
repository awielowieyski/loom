"""Tests for BreakingChangeDetector — detecting capability regressions from skill amendments."""

import uuid
from unittest.mock import AsyncMock, MagicMock

from loom.models.behavioral import (
    BreakingChangeReport,
    ComparativeAxisScores,
    ComparativeResult,
    ComparisonSummary,
)
from loom.models.common import EvalScenario, EvalSpec
from loom.services.breaking_change_detector import BreakingChangeDetector

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_skill(
    slug: str = "test-skill",
    content: str = "# Step 1\nDo something",
    version: str = "1.0.0",
) -> MagicMock:
    skill = MagicMock()
    skill.id = uuid.uuid4()
    skill.slug = slug
    skill.content = content
    skill.version = version
    return skill


def _make_capability(
    slug: str = "test-cap",
    name: str = "Test Capability",
    skill_refs: list[str] | None = None,
    scenarios: list[dict[str, str]] | None = None,
) -> MagicMock:
    """Create a mock Capability with steps referencing skills."""
    if skill_refs is None:
        skill_refs = ["loom://test-skill"]
    if scenarios is None:
        scenarios = [
            {
                "description": "Cap scenario",
                "input_context": "context",
                "success_criteria": "works",
            }
        ]

    steps = []
    for ref in skill_refs:
        step = MagicMock()
        step.skill_ref = ref
        steps.append(step)

    cap = MagicMock()
    cap.slug = slug
    cap.name = name
    cap.steps = steps
    cap.eval_spec = EvalSpec(scenarios=[EvalScenario(**s) for s in scenarios])
    return cap


def _make_comparison_summary(
    skill_a_id: uuid.UUID,
    skill_b_id: uuid.UUID,
    winners: list[str],
) -> ComparisonSummary:
    results = []
    for i, winner in enumerate(winners):
        # When old (a) wins, old has higher scores
        if winner == "a":
            score_a = ComparativeAxisScores(
                outcome_quality=0.9, completeness=0.9, efficiency=0.9, safety=1.0
            )
            score_b = ComparativeAxisScores(
                outcome_quality=0.5, completeness=0.5, efficiency=0.5, safety=1.0
            )
        elif winner == "b":
            score_a = ComparativeAxisScores(
                outcome_quality=0.5, completeness=0.5, efficiency=0.5, safety=1.0
            )
            score_b = ComparativeAxisScores(
                outcome_quality=0.9, completeness=0.9, efficiency=0.9, safety=1.0
            )
        else:
            score_a = ComparativeAxisScores(
                outcome_quality=0.7, completeness=0.7, efficiency=0.7, safety=1.0
            )
            score_b = ComparativeAxisScores(
                outcome_quality=0.7, completeness=0.7, efficiency=0.7, safety=1.0
            )

        results.append(
            ComparativeResult(
                id=uuid.uuid4(),
                skill_a_id=skill_a_id,
                skill_a_version="1.0.0",
                skill_b_id=skill_b_id,
                skill_b_version="2.0.0",
                scenario_index=i,
                winner=winner,
                score_a=score_a,
                score_b=score_b,
                preference_confidence=0.85,
                reasoning="comparison",
                judge_model_id="test-judge",
            )
        )

    win_a = sum(1 for w in winners if w == "a")
    win_b = sum(1 for w in winners if w == "b")
    tie = sum(1 for w in winners if w == "tie")
    overall = "a" if win_a > win_b else ("b" if win_b > win_a else "tie")

    return ComparisonSummary(
        skill_a_id=skill_a_id,
        skill_b_id=skill_b_id,
        per_scenario=results,
        overall_winner=overall,
        win_count_a=win_a,
        win_count_b=win_b,
        tie_count=tie,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBreakingChangeDetector:
    """BreakingChangeDetector tests."""

    async def test_no_capabilities_referencing_skill_returns_empty(self) -> None:
        """No capabilities referencing the skill -> empty report list."""
        cap_repo = AsyncMock()
        cap_repo.search_by_skill_ref = AsyncMock(return_value=[])
        comp_service = AsyncMock()

        detector = BreakingChangeDetector(
            capability_repo=cap_repo,
            comparative_eval=comp_service,
        )

        old_skill = _make_skill(slug="my-skill", version="1.0.0")
        new_skill = _make_skill(slug="my-skill", version="2.0.0")

        reports = await detector.detect("my-skill", old_skill, new_skill)

        assert reports == []
        comp_service.compare.assert_not_called()

    async def test_detects_breaking_change_when_score_drops(self) -> None:
        """Flags breaking change when old skill outperforms new on capability scenarios."""
        old_skill = _make_skill(slug="my-skill", version="1.0.0")
        new_skill = _make_skill(slug="my-skill", version="2.0.0")

        cap = _make_capability(slug="test-cap", skill_refs=["loom://my-skill"])

        cap_repo = AsyncMock()
        cap_repo.search_by_skill_ref = AsyncMock(return_value=[cap])

        # Old skill wins on both scenarios -> new is worse
        summary = _make_comparison_summary(old_skill.id, new_skill.id, ["a", "a"])
        comp_service = AsyncMock()
        comp_service.compare = AsyncMock(return_value=summary)

        detector = BreakingChangeDetector(
            capability_repo=cap_repo,
            comparative_eval=comp_service,
        )

        reports = await detector.detect("my-skill", old_skill, new_skill)

        assert len(reports) == 1
        report = reports[0]
        assert isinstance(report, BreakingChangeReport)
        assert report.capability_slug == "test-cap"
        assert report.step_index == 0
        assert report.score_delta < 0  # new is worse
        assert report.degraded_scenarios == [0, 1]

    async def test_no_breaking_change_when_new_is_better(self) -> None:
        """No breaking change report when new skill is equal or better."""
        old_skill = _make_skill(slug="my-skill", version="1.0.0")
        new_skill = _make_skill(slug="my-skill", version="2.0.0")

        cap = _make_capability(slug="test-cap", skill_refs=["loom://my-skill"])

        cap_repo = AsyncMock()
        cap_repo.search_by_skill_ref = AsyncMock(return_value=[cap])

        # New skill wins both scenarios -> no breaking change
        summary = _make_comparison_summary(old_skill.id, new_skill.id, ["b", "b"])
        comp_service = AsyncMock()
        comp_service.compare = AsyncMock(return_value=summary)

        detector = BreakingChangeDetector(
            capability_repo=cap_repo,
            comparative_eval=comp_service,
        )

        reports = await detector.detect("my-skill", old_skill, new_skill)

        assert reports == []

    async def test_multiple_capabilities_checked_independently(self) -> None:
        """Each affected capability is checked independently."""
        old_skill = _make_skill(slug="my-skill", version="1.0.0")
        new_skill = _make_skill(slug="my-skill", version="2.0.0")

        cap1 = _make_capability(slug="cap-a", name="Cap A", skill_refs=["loom://my-skill"])
        cap2 = _make_capability(slug="cap-b", name="Cap B", skill_refs=["loom://my-skill"])

        cap_repo = AsyncMock()
        cap_repo.search_by_skill_ref = AsyncMock(return_value=[cap1, cap2])

        # Cap1: old wins (breaking), Cap2: new wins (safe)
        summary_breaking = _make_comparison_summary(old_skill.id, new_skill.id, ["a"])
        summary_safe = _make_comparison_summary(old_skill.id, new_skill.id, ["b"])

        comp_service = AsyncMock()
        comp_service.compare = AsyncMock(side_effect=[summary_breaking, summary_safe])

        detector = BreakingChangeDetector(
            capability_repo=cap_repo,
            comparative_eval=comp_service,
        )

        reports = await detector.detect("my-skill", old_skill, new_skill)

        # Only cap1 should have a breaking change
        assert len(reports) == 1
        assert reports[0].capability_slug == "cap-a"
        assert comp_service.compare.call_count == 2
