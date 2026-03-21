"""Tests for DiscoveryService with constraint-aware ranking."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from loom.models.common import CostProfile, TrustTier
from loom.models.resolution import ResolutionContext, ResolutionError, ResolvedSkill
from loom.models.skill import Skill, SkillSummary
from loom.services.discovery import DiscoveryService


def _make_skill_summary(
    slug: str,
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


def _make_skill(
    slug: str,
    trust_tier: TrustTier = TrustTier.COMMUNITY,
    cost_profile: CostProfile = CostProfile.FREE,
) -> Skill:
    skill_id = uuid.uuid4()
    return Skill(
        id=skill_id,
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
def mock_embedder() -> AsyncMock:
    embedder = MagicMock()
    embed_result = MagicMock()
    embed_result.embeddings = [[0.1] * 1536]
    embedder.embed_query = AsyncMock(return_value=embed_result)
    return embedder


@pytest.fixture
def mock_repo() -> AsyncMock:
    repo = MagicMock()
    repo.vector_search = AsyncMock(return_value=[])
    return repo


async def test_resolve_returns_best_match(mock_repo: MagicMock, mock_embedder: MagicMock) -> None:
    skill = _make_skill("best-match")
    mock_repo.vector_search = AsyncMock(return_value=[skill])

    service = DiscoveryService(skill_repo=mock_repo, embedder=mock_embedder)
    result = await service.resolve("do something")

    assert isinstance(result, ResolvedSkill)
    assert result.skill.slug == "best-match"


async def test_resolve_no_candidates_returns_error(
    mock_repo: MagicMock, mock_embedder: MagicMock
) -> None:
    mock_repo.vector_search = AsyncMock(return_value=[])

    service = DiscoveryService(skill_repo=mock_repo, embedder=mock_embedder)
    result = await service.resolve("do something")

    assert isinstance(result, ResolutionError)
    assert result.error == "no_match"


async def test_resolve_filters_by_trust_floor(
    mock_repo: MagicMock, mock_embedder: MagicMock
) -> None:
    experimental = _make_skill("experimental-skill", trust_tier=TrustTier.EXPERIMENTAL)
    community = _make_skill("community-skill", trust_tier=TrustTier.COMMUNITY)
    mock_repo.vector_search = AsyncMock(return_value=[experimental, community])

    context = ResolutionContext(trust_floor=TrustTier.COMMUNITY)
    service = DiscoveryService(skill_repo=mock_repo, embedder=mock_embedder)
    result = await service.resolve("do something", context=context)

    assert isinstance(result, ResolvedSkill)
    assert result.skill.slug == "community-skill"
    # experimental should be in rejected_candidates
    rejected_slugs = [r.skill.slug for r in result.rejected_candidates]
    assert "experimental-skill" in rejected_slugs


async def test_resolve_penalises_high_cost(mock_repo: MagicMock, mock_embedder: MagicMock) -> None:
    expensive = _make_skill("expensive-skill", cost_profile=CostProfile.HIGH)
    cheap = _make_skill("cheap-skill", cost_profile=CostProfile.FREE)
    mock_repo.vector_search = AsyncMock(return_value=[expensive, cheap])

    context = ResolutionContext(cost_budget=CostProfile.LOW)
    service = DiscoveryService(skill_repo=mock_repo, embedder=mock_embedder)
    result = await service.resolve("do something", context=context)

    # cheap should be ranked higher than expensive
    assert isinstance(result, ResolvedSkill)
    assert result.skill.slug == "cheap-skill"
