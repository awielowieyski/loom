"""Tests for contextual rejection rationale in discovery services."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from loom.models.capability import CapabilitySummary
from loom.models.common import CostProfile, TrustTier
from loom.models.skill import Skill, SkillSummary
from loom.services.capability_discovery import _build_capability_tradeoff
from loom.services.discovery import DiscoveryService, _build_tradeoff

# ---------------------------------------------------------------------------
# _build_tradeoff (skill) tests
# ---------------------------------------------------------------------------


def _make_skill_summary(
    slug: str = "alt",
    trust_tier: TrustTier = TrustTier.COMMUNITY,
    cost_profile: CostProfile = CostProfile.FREE,
) -> SkillSummary:
    return SkillSummary(
        id=uuid.uuid4(),
        slug=slug,
        name=slug,
        description=f"Description for {slug}",
        category_id=uuid.uuid4(),
        tags=[],
        version="1.0.0",
        trust_tier=trust_tier,
        cost_profile=cost_profile,
        estimated_duration="fast",
    )


def test_tradeoff_score_gap() -> None:
    """Shows score gap when alt has lower score."""
    alt = _make_skill_summary("alt")
    winner = _make_skill_summary("winner")
    result = _build_tradeoff(alt, 0.50, winner, 1.00)
    assert "Lower relevance" in result
    assert "0.50" in result
    assert "1.00" in result


def test_tradeoff_different_trust_tier() -> None:
    """Shows trust tier difference."""
    alt = _make_skill_summary("alt", trust_tier=TrustTier.EXPERIMENTAL)
    winner = _make_skill_summary("winner", trust_tier=TrustTier.VERIFIED)
    result = _build_tradeoff(alt, 1.0, winner, 1.0)
    assert "Trust tier: experimental (winner: verified)" in result


def test_tradeoff_higher_cost() -> None:
    """Shows cost difference when alt is more expensive."""
    alt = _make_skill_summary("alt", cost_profile=CostProfile.HIGH)
    winner = _make_skill_summary("winner", cost_profile=CostProfile.FREE)
    result = _build_tradeoff(alt, 1.0, winner, 1.0)
    assert "Higher cost (high vs free)" in result


def test_tradeoff_multiple_reasons() -> None:
    """Combines multiple reasons with semicolons."""
    alt = _make_skill_summary(
        "alt", trust_tier=TrustTier.EXPERIMENTAL, cost_profile=CostProfile.HIGH
    )
    winner = _make_skill_summary(
        "winner", trust_tier=TrustTier.VERIFIED, cost_profile=CostProfile.FREE
    )
    result = _build_tradeoff(alt, 0.5, winner, 1.0)
    assert "; " in result
    assert "Lower relevance" in result
    assert "Trust tier" in result
    assert "Higher cost" in result


def test_tradeoff_fallback() -> None:
    """Falls back to 'Lower match score' when no specific differences."""
    alt = _make_skill_summary("alt")
    winner = _make_skill_summary("winner")
    result = _build_tradeoff(alt, 1.0, winner, 1.0)
    assert result == "Lower match score"


def test_tradeoff_no_cost_flag_when_alt_cheaper() -> None:
    """Does not flag cost when alt is cheaper than winner."""
    alt = _make_skill_summary("alt", cost_profile=CostProfile.FREE)
    winner = _make_skill_summary("winner", cost_profile=CostProfile.HIGH)
    result = _build_tradeoff(alt, 1.0, winner, 1.0)
    assert "Higher cost" not in result


# ---------------------------------------------------------------------------
# _build_capability_tradeoff tests
# ---------------------------------------------------------------------------


def _make_cap_summary(
    slug: str = "alt-cap",
    trust_tier: TrustTier = TrustTier.COMMUNITY,
    cost_profile: CostProfile = CostProfile.FREE,
) -> CapabilitySummary:
    return CapabilitySummary(
        id=uuid.uuid4(),
        slug=slug,
        name=slug,
        description=f"Description for {slug}",
        category_id=uuid.uuid4(),
        tags=[],
        version="1.0.0",
        trust_tier=trust_tier,
        cost_profile=cost_profile,
        estimated_duration="slow",
        step_count=2,
    )


def test_capability_tradeoff_score_gap() -> None:
    """Capability tradeoff shows score gap."""
    alt = _make_cap_summary("alt-cap")
    winner = _make_cap_summary("winner-cap")
    result = _build_capability_tradeoff(alt, 0.50, winner, 1.00)
    assert "Lower relevance" in result


def test_capability_tradeoff_trust_and_cost() -> None:
    """Capability tradeoff shows trust and cost differences."""
    alt = _make_cap_summary(
        "alt-cap", trust_tier=TrustTier.EXPERIMENTAL, cost_profile=CostProfile.MODERATE
    )
    winner = _make_cap_summary(
        "winner-cap", trust_tier=TrustTier.COMMUNITY, cost_profile=CostProfile.FREE
    )
    result = _build_capability_tradeoff(alt, 1.0, winner, 1.0)
    assert "Trust tier: experimental (winner: community)" in result
    assert "Higher cost (moderate vs free)" in result


def test_capability_tradeoff_fallback() -> None:
    """Capability tradeoff falls back when no differences."""
    alt = _make_cap_summary("alt-cap")
    winner = _make_cap_summary("winner-cap")
    result = _build_capability_tradeoff(alt, 1.0, winner, 1.0)
    assert result == "Lower match score"


# ---------------------------------------------------------------------------
# Integration: DiscoveryService.resolve produces contextual tradeoffs
# ---------------------------------------------------------------------------


def _make_full_skill(
    slug: str,
    skill_id: uuid.UUID | None = None,
    trust_tier: TrustTier = TrustTier.COMMUNITY,
    cost_profile: CostProfile = CostProfile.FREE,
) -> Skill:
    return Skill(
        id=skill_id or uuid.uuid4(),
        slug=slug,
        name=slug,
        description=f"Description for {slug}",
        content=f"Content for {slug}",
        category_id=uuid.uuid4(),
        tags=[],
        scope="community",
        version="1.0.0",
        author_id=uuid.uuid4(),
        trust_tier=trust_tier,
        cost_profile=cost_profile,
        cost_drivers=[],
        estimated_duration="fast",
        dependencies={},
        eval_spec={},
    )


@pytest.fixture
def mock_embedder() -> MagicMock:
    embedder = MagicMock()
    embed_result = MagicMock()
    embed_result.embeddings = [[0.1] * 1536]
    embedder.embed_query = AsyncMock(return_value=embed_result)
    return embedder


async def test_discovery_resolve_produces_contextual_tradeoffs(mock_embedder: MagicMock) -> None:
    """DiscoveryService.resolve produces contextual tradeoff strings, not static ones."""
    winner_id = uuid.uuid4()
    alt_id = uuid.uuid4()
    winner_summary = SkillSummary(
        id=winner_id,
        slug="winner",
        name="winner",
        description="Winner skill",
        category_id=uuid.uuid4(),
        tags=[],
        version="1.0.0",
        trust_tier=TrustTier.VERIFIED,
        cost_profile=CostProfile.FREE,
        estimated_duration="fast",
    )
    alt_summary = SkillSummary(
        id=alt_id,
        slug="alt",
        name="alt",
        description="Alt skill",
        category_id=uuid.uuid4(),
        tags=[],
        version="1.0.0",
        trust_tier=TrustTier.EXPERIMENTAL,
        cost_profile=CostProfile.HIGH,
        estimated_duration="fast",
    )

    repo = MagicMock()
    repo.vector_search_summary = AsyncMock(return_value=[winner_summary, alt_summary])
    repo.get_by_id = AsyncMock(return_value=_make_full_skill("winner", skill_id=winner_id))

    svc = DiscoveryService(skill_repo=repo, embedder=mock_embedder)
    result = await svc.resolve("do something")

    # Should not use static "Alternative skill" anymore
    from loom.models.resolution import ResolvedSkill

    assert isinstance(result, ResolvedSkill)
    assert len(result.alternatives) == 1
    alt = result.alternatives[0]
    assert alt.tradeoff != "Alternative skill"
    assert "Trust tier" in alt.tradeoff
    assert "Higher cost" in alt.tradeoff
