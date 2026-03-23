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
    skill_id: uuid.UUID | None = None,
) -> SkillSummary:
    return SkillSummary(
        id=skill_id or uuid.uuid4(),
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
    skill_id: uuid.UUID | None = None,
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
def mock_embedder() -> AsyncMock:
    embedder = MagicMock()
    embed_result = MagicMock()
    embed_result.embeddings = [[0.1] * 1536]
    embedder.embed_query = AsyncMock(return_value=embed_result)
    return embedder


@pytest.fixture
def mock_repo() -> AsyncMock:
    repo = MagicMock()
    repo.vector_search_summary = AsyncMock(return_value=[])
    repo.get_by_id = AsyncMock(return_value=None)
    return repo


async def test_resolve_returns_best_match(mock_repo: MagicMock, mock_embedder: MagicMock) -> None:
    skill_id = uuid.uuid4()
    summary = _make_skill_summary("best-match", skill_id=skill_id)
    full_skill = _make_skill("best-match", skill_id=skill_id)
    mock_repo.vector_search_summary = AsyncMock(return_value=[summary])
    mock_repo.get_by_id = AsyncMock(return_value=full_skill)

    service = DiscoveryService(skill_repo=mock_repo, embedder=mock_embedder)
    result = await service.resolve("do something")

    assert isinstance(result, ResolvedSkill)
    assert result.skill.slug == "best-match"


async def test_resolve_no_candidates_returns_error(
    mock_repo: MagicMock, mock_embedder: MagicMock
) -> None:
    mock_repo.vector_search_summary = AsyncMock(return_value=[])

    service = DiscoveryService(skill_repo=mock_repo, embedder=mock_embedder)
    result = await service.resolve("do something")

    assert isinstance(result, ResolutionError)
    assert result.error == "no_match"


async def test_resolve_filters_by_trust_floor(
    mock_repo: MagicMock, mock_embedder: MagicMock
) -> None:
    community_id = uuid.uuid4()
    experimental = _make_skill_summary("experimental-skill", trust_tier=TrustTier.EXPERIMENTAL)
    community = _make_skill_summary(
        "community-skill", trust_tier=TrustTier.COMMUNITY, skill_id=community_id
    )
    full_community = _make_skill(
        "community-skill", trust_tier=TrustTier.COMMUNITY, skill_id=community_id
    )
    mock_repo.vector_search_summary = AsyncMock(return_value=[experimental, community])
    mock_repo.get_by_id = AsyncMock(return_value=full_community)

    context = ResolutionContext(trust_floor=TrustTier.COMMUNITY)
    service = DiscoveryService(skill_repo=mock_repo, embedder=mock_embedder)
    result = await service.resolve("do something", context=context)

    assert isinstance(result, ResolvedSkill)
    assert result.skill.slug == "community-skill"
    # experimental should be in rejected_candidates
    rejected_slugs = [r.skill.slug for r in result.rejected_candidates]
    assert "experimental-skill" in rejected_slugs


async def test_resolve_penalises_high_cost(mock_repo: MagicMock, mock_embedder: MagicMock) -> None:
    cheap_id = uuid.uuid4()
    expensive = _make_skill_summary("expensive-skill", cost_profile=CostProfile.HIGH)
    cheap = _make_skill_summary("cheap-skill", cost_profile=CostProfile.FREE, skill_id=cheap_id)
    full_cheap = _make_skill("cheap-skill", cost_profile=CostProfile.FREE, skill_id=cheap_id)
    mock_repo.vector_search_summary = AsyncMock(return_value=[expensive, cheap])
    mock_repo.get_by_id = AsyncMock(return_value=full_cheap)

    context = ResolutionContext(cost_budget=CostProfile.LOW)
    service = DiscoveryService(skill_repo=mock_repo, embedder=mock_embedder)
    result = await service.resolve("do something", context=context)

    # cheap should be ranked higher than expensive
    assert isinstance(result, ResolvedSkill)
    assert result.skill.slug == "cheap-skill"


async def test_embedding_cache_avoids_redundant_calls(
    mock_repo: MagicMock, mock_embedder: MagicMock
) -> None:
    """Identical queries should only call the embedder once."""
    mock_repo.vector_search_summary = AsyncMock(return_value=[])

    service = DiscoveryService(skill_repo=mock_repo, embedder=mock_embedder)
    await service.resolve("same query")
    await service.resolve("same query")

    # embedder should only have been called once due to cache
    assert mock_embedder.embed_query.call_count == 1
