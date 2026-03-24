"""Tests for UnifiedResolver — Task 10."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from loom.models.capability import Capability, CapabilityStep, CapabilitySummary
from loom.models.common import CostProfile, TrustTier
from loom.models.resolution import (
    ResolutionError,
    ResolvedCapability,
    ResolvedResult,
    ResolvedSkill,
    ResolvedStep,
)
from loom.models.skill import Skill, SkillSummary
from loom.services.unified_resolver import UnifiedResolver


def _make_skill(slug: str = "test-skill") -> Skill:
    return Skill(
        id=uuid.uuid4(),
        slug=slug,
        name=slug,
        description=f"Description for {slug}",
        content=f"Content for {slug}",
        category_id=uuid.uuid4(),
        tags=[],
        scope="community",
        version="1.0.0",
        author_id=uuid.uuid4(),
        trust_tier=TrustTier.COMMUNITY,
        cost_profile=CostProfile.FREE,
        cost_drivers=[],
        estimated_duration="fast",
    )


def _make_resolved_skill(
    slug: str = "test-skill",
    rationale: list[str] | None = None,
) -> ResolvedSkill:
    return ResolvedSkill(
        skill=_make_skill(slug),
        selection_rationale=rationale or [f"Selected {slug!r} as best match"],
    )


def _make_resolved_capability(
    slug: str = "test-cap",
    rationale: list[str] | None = None,
) -> ResolvedCapability:
    skill = _make_skill("step-skill")
    cap = Capability(
        id=uuid.uuid4(),
        slug=slug,
        name=slug,
        description=f"Description for {slug}",
        category_id=uuid.uuid4(),
        tags=[],
        scope="community",
        version="1.0.0",
        author_id=uuid.uuid4(),
        trust_tier=TrustTier.COMMUNITY,
        steps=[CapabilityStep(skill_ref="loom://step-skill", role="Do thing")],
        preconditions=[],
        expected_outcome="",
        data_flow=[],
        cost_profile=CostProfile.FREE,
        cost_drivers=[],
        estimated_duration="slow",
    )
    return ResolvedCapability(
        capability=cap,
        resolved_steps=[
            ResolvedStep(
                index=0,
                skill_ref="loom://step-skill",
                role="Do thing",
                skill=skill,
                inputs={},
                outputs={},
                required=True,
                data_classification="internal",
            )
        ],
        effective_trust_tier=TrustTier.COMMUNITY,
        data_flow=[],
        selection_rationale=rationale or [f"Selected {slug!r} as best match"],
    )


def _make_capability_summary(slug: str = "test-cap") -> CapabilitySummary:
    return CapabilitySummary(
        id=uuid.uuid4(),
        slug=slug,
        name=slug,
        description=f"Description for {slug}",
        category_id=uuid.uuid4(),
        tags=[],
        version="1.0.0",
        trust_tier=TrustTier.COMMUNITY,
        cost_profile=CostProfile.FREE,
        estimated_duration="slow",
        step_count=1,
    )


def _make_skill_summary(slug: str = "test-skill") -> SkillSummary:
    return SkillSummary(
        id=uuid.uuid4(),
        slug=slug,
        name=slug,
        description=f"Description for {slug}",
        category_id=uuid.uuid4(),
        tags=[],
        version="1.0.0",
        trust_tier=TrustTier.COMMUNITY,
        cost_profile=CostProfile.FREE,
        estimated_duration="fast",
    )


@pytest.fixture
def mock_skill_service() -> MagicMock:
    svc = MagicMock()
    svc.resolve = AsyncMock(
        return_value=ResolutionError(error="no_match", message="No skills found")
    )
    svc.search = AsyncMock(return_value=[])
    return svc


@pytest.fixture
def mock_cap_service() -> MagicMock:
    svc = MagicMock()
    svc.resolve = AsyncMock(
        return_value=ResolutionError(error="no_match", message="No capabilities found")
    )
    svc.search = AsyncMock(return_value=[])
    return svc


# ---------------------------------------------------------------------------
# resolve() tests
# ---------------------------------------------------------------------------


async def test_resolve_returns_skill_when_skill_matches_best(
    mock_skill_service: MagicMock,
    mock_cap_service: MagicMock,
) -> None:
    """Resolve returns ResolvedResult with type='skill' when a skill matches."""
    resolved_skill = _make_resolved_skill("best-skill")
    mock_skill_service.resolve = AsyncMock(return_value=resolved_skill)

    resolver = UnifiedResolver(
        discovery_service=mock_skill_service,
        capability_discovery_service=mock_cap_service,
    )
    result = await resolver.resolve("do something")

    assert isinstance(result, ResolvedResult)
    assert result.type == "skill"
    assert result.skill is not None
    assert result.skill.skill.slug == "best-skill"


async def test_resolve_returns_capability_when_capability_matches_best(
    mock_skill_service: MagicMock,
    mock_cap_service: MagicMock,
) -> None:
    """Resolve returns ResolvedResult with type='capability' when a capability matches."""
    resolved_cap = _make_resolved_capability("best-cap")
    mock_cap_service.resolve = AsyncMock(return_value=resolved_cap)

    resolver = UnifiedResolver(
        discovery_service=mock_skill_service,
        capability_discovery_service=mock_cap_service,
    )
    result = await resolver.resolve("do something")

    assert isinstance(result, ResolvedResult)
    assert result.type == "capability"
    assert result.capability is not None
    assert result.capability.capability.slug == "best-cap"


async def test_resolve_type_filter_skill_excludes_capabilities(
    mock_skill_service: MagicMock,
    mock_cap_service: MagicMock,
) -> None:
    """Type filter 'skill' does not query capability service."""
    resolved_skill = _make_resolved_skill("only-skill")
    mock_skill_service.resolve = AsyncMock(return_value=resolved_skill)

    resolver = UnifiedResolver(
        discovery_service=mock_skill_service,
        capability_discovery_service=mock_cap_service,
    )
    result = await resolver.resolve("do something", type_filter="skill")

    assert isinstance(result, ResolvedResult)
    assert result.type == "skill"
    mock_cap_service.resolve.assert_not_called()


async def test_resolve_type_filter_capability_excludes_skills(
    mock_skill_service: MagicMock,
    mock_cap_service: MagicMock,
) -> None:
    """Type filter 'capability' does not query skill service."""
    resolved_cap = _make_resolved_capability("only-cap")
    mock_cap_service.resolve = AsyncMock(return_value=resolved_cap)

    resolver = UnifiedResolver(
        discovery_service=mock_skill_service,
        capability_discovery_service=mock_cap_service,
    )
    result = await resolver.resolve("do something", type_filter="capability")

    assert isinstance(result, ResolvedResult)
    assert result.type == "capability"
    mock_skill_service.resolve.assert_not_called()


async def test_resolve_type_filter_any_queries_both(
    mock_skill_service: MagicMock,
    mock_cap_service: MagicMock,
) -> None:
    """Type filter 'any' queries both services."""
    resolver = UnifiedResolver(
        discovery_service=mock_skill_service,
        capability_discovery_service=mock_cap_service,
    )
    await resolver.resolve("do something", type_filter="any")

    mock_skill_service.resolve.assert_called_once()
    mock_cap_service.resolve.assert_called_once()


async def test_resolve_both_match_prefers_capability_with_more_rationale(
    mock_skill_service: MagicMock,
    mock_cap_service: MagicMock,
) -> None:
    """When both match, the one with more selection_rationale wins."""
    resolved_skill = _make_resolved_skill("simple-skill", rationale=["Selected 'simple-skill'"])
    resolved_cap = _make_resolved_capability(
        "rich-cap",
        rationale=[
            "Selected 'rich-cap'",
            "Cost budget: free",
            "Trust floor: community",
        ],
    )
    mock_skill_service.resolve = AsyncMock(return_value=resolved_skill)
    mock_cap_service.resolve = AsyncMock(return_value=resolved_cap)

    resolver = UnifiedResolver(
        discovery_service=mock_skill_service,
        capability_discovery_service=mock_cap_service,
    )
    result = await resolver.resolve("do something")

    assert isinstance(result, ResolvedResult)
    assert result.type == "capability"


async def test_resolve_both_match_prefers_skill_when_equal_rationale(
    mock_skill_service: MagicMock,
    mock_cap_service: MagicMock,
) -> None:
    """When both match with equal rationale, skill wins (simpler is preferred)."""
    resolved_skill = _make_resolved_skill("simple-skill")
    resolved_cap = _make_resolved_capability("simple-cap")
    mock_skill_service.resolve = AsyncMock(return_value=resolved_skill)
    mock_cap_service.resolve = AsyncMock(return_value=resolved_cap)

    resolver = UnifiedResolver(
        discovery_service=mock_skill_service,
        capability_discovery_service=mock_cap_service,
    )
    result = await resolver.resolve("do something")

    assert isinstance(result, ResolvedResult)
    assert result.type == "skill"


async def test_resolve_neither_matches_returns_error(
    mock_skill_service: MagicMock,
    mock_cap_service: MagicMock,
) -> None:
    """When neither service matches, return ResolutionError."""
    resolver = UnifiedResolver(
        discovery_service=mock_skill_service,
        capability_discovery_service=mock_cap_service,
    )
    result = await resolver.resolve("nothing matches")

    assert isinstance(result, ResolutionError)
    assert result.error == "no_match"


# ---------------------------------------------------------------------------
# search() tests
# ---------------------------------------------------------------------------


async def test_search_type_any_returns_both(
    mock_skill_service: MagicMock,
    mock_cap_service: MagicMock,
) -> None:
    """Search with type_filter='any' returns skills and capabilities."""
    mock_skill_service.search = AsyncMock(return_value=[_make_skill_summary("s1")])
    mock_cap_service.search = AsyncMock(return_value=[_make_capability_summary("c1")])

    resolver = UnifiedResolver(
        discovery_service=mock_skill_service,
        capability_discovery_service=mock_cap_service,
    )
    results = await resolver.search("deploy")

    assert len(results) == 2


async def test_search_type_skill_excludes_capabilities(
    mock_skill_service: MagicMock,
    mock_cap_service: MagicMock,
) -> None:
    """Search with type_filter='skill' only queries skill service."""
    mock_skill_service.search = AsyncMock(return_value=[_make_skill_summary("s1")])

    resolver = UnifiedResolver(
        discovery_service=mock_skill_service,
        capability_discovery_service=mock_cap_service,
    )
    results = await resolver.search("deploy", type_filter="skill")

    assert len(results) == 1
    mock_cap_service.search.assert_not_called()


async def test_search_type_capability_excludes_skills(
    mock_skill_service: MagicMock,
    mock_cap_service: MagicMock,
) -> None:
    """Search with type_filter='capability' only queries capability service."""
    mock_cap_service.search = AsyncMock(return_value=[_make_capability_summary("c1")])

    resolver = UnifiedResolver(
        discovery_service=mock_skill_service,
        capability_discovery_service=mock_cap_service,
    )
    results = await resolver.search("deploy", type_filter="capability")

    assert len(results) == 1
    mock_skill_service.search.assert_not_called()
