import uuid

from loom.models.common import CostProfile, TrustTier
from loom.models.resolution import (
    ResolutionContext,
    ResolutionError,
    ResolvedSkill,
)
from loom.models.skill import Skill


def _make_skill(**overrides: object) -> Skill:
    defaults: dict[str, object] = dict(
        id=uuid.uuid4(),
        slug="test-skill",
        name="Test",
        description="Test skill",
        content="# Test",
        category_id=uuid.uuid4(),
        tags=[],
        scope="community",
        version="1.0.0",
        author_id=uuid.uuid4(),
        trust_tier=TrustTier.EXPERIMENTAL,
        cost_profile=CostProfile.FREE,
        cost_drivers=[],
        estimated_duration="fast",
        dependencies={},
        eval_spec={},
    )
    defaults.update(overrides)
    return Skill(**defaults)


def test_resolution_context_minimal() -> None:
    ctx = ResolutionContext()
    assert ctx.trust_floor is None
    assert ctx.available_tools == []


def test_resolution_context_full() -> None:
    ctx = ResolutionContext(
        trust_floor=TrustTier.COMMUNITY,
        cost_budget=CostProfile.LOW,
        available_tools=["filesystem", "git"],
    )
    assert ctx.trust_floor == TrustTier.COMMUNITY
    assert "git" in ctx.available_tools


def test_resolved_skill() -> None:
    skill = _make_skill()
    resolved = ResolvedSkill(
        skill=skill,
        dependencies_satisfied=["filesystem"],
        dependencies_missing=["github-api"],
        alternatives=[],
        rejected_candidates=[],
        selection_rationale=["Matched task", "All deps met"],
    )
    assert resolved.skill.slug == "test-skill"
    assert "Matched task" in resolved.selection_rationale


def test_resolution_error() -> None:
    err = ResolutionError(
        error="no_match",
        message="No skills found",
        suggestions=["Try broader terms"],
    )
    assert err.error == "no_match"
