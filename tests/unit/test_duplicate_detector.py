"""Tests for the DuplicateDetector service."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from loom.services.duplicate_detector import (
    DuplicateDetector,
    cosine_similarity,
)


def _make_summary(slug: str = "existing-skill", skill_id: uuid.UUID | None = None):
    """Create a mock SkillSummary."""
    s = MagicMock()
    s.id = skill_id or uuid.uuid4()
    s.slug = slug
    return s


def _make_full_skill(slug: str, embedding: list[float], skill_id: uuid.UUID | None = None):
    """Create a mock Skill with embedding."""
    s = MagicMock()
    s.id = skill_id or uuid.uuid4()
    s.slug = slug
    s.embedding = embedding
    return s


@pytest.fixture
def embedder():
    """Mock embedder that returns a known embedding."""
    e = AsyncMock()
    # Default: return a simple unit vector
    e.embed.return_value = [1.0, 0.0, 0.0]
    return e


@pytest.fixture
def skill_repo():
    return AsyncMock()


def test_cosine_similarity_identical():
    """Identical vectors have similarity 1.0."""
    a = [1.0, 2.0, 3.0]
    assert abs(cosine_similarity(a, a) - 1.0) < 1e-9


def test_cosine_similarity_orthogonal():
    """Orthogonal vectors have similarity 0.0."""
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert abs(cosine_similarity(a, b)) < 1e-9


def test_cosine_similarity_zero_vector():
    """Zero vector returns 0.0."""
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


@pytest.mark.asyncio
async def test_reject_above_threshold(skill_repo, embedder):
    """Similarity > reject_threshold returns action='reject'."""
    sid = uuid.uuid4()
    summary = _make_summary("near-dupe", skill_id=sid)
    full_skill = _make_full_skill("near-dupe", [1.0, 0.0, 0.0], skill_id=sid)

    skill_repo.vector_search_summary.return_value = [summary]
    skill_repo.get_by_id.return_value = full_skill

    # Embedder returns exact same vector -> similarity = 1.0
    embedder.embed.return_value = [1.0, 0.0, 0.0]

    detector = DuplicateDetector(skill_repo, embedder, reject_threshold=0.95, warn_threshold=0.85)
    result = await detector.check("some content")

    assert result.action == "reject"
    assert result.most_similar_slug == "near-dupe"
    assert result.similarity > 0.95


@pytest.mark.asyncio
async def test_flag_between_thresholds(skill_repo, embedder):
    """Similarity between warn and reject threshold returns action='flag'."""
    sid = uuid.uuid4()
    summary = _make_summary("similar-skill", skill_id=sid)
    # Slightly different vector -> similarity ~0.9
    full_skill = _make_full_skill("similar-skill", [0.9, 0.4, 0.1], skill_id=sid)

    skill_repo.vector_search_summary.return_value = [summary]
    skill_repo.get_by_id.return_value = full_skill

    embedder.embed.return_value = [1.0, 0.0, 0.0]

    detector = DuplicateDetector(skill_repo, embedder, reject_threshold=0.95, warn_threshold=0.85)
    result = await detector.check("some content")

    assert result.action == "flag"
    assert result.most_similar_slug == "similar-skill"
    assert 0.85 < result.similarity < 0.95


@pytest.mark.asyncio
async def test_accept_below_threshold(skill_repo, embedder):
    """Similarity below warn threshold returns action='accept'."""
    sid = uuid.uuid4()
    summary = _make_summary("different-skill", skill_id=sid)
    # Very different vector -> low similarity
    full_skill = _make_full_skill("different-skill", [0.0, 0.0, 1.0], skill_id=sid)

    skill_repo.vector_search_summary.return_value = [summary]
    skill_repo.get_by_id.return_value = full_skill

    embedder.embed.return_value = [1.0, 0.0, 0.0]

    detector = DuplicateDetector(skill_repo, embedder, reject_threshold=0.95, warn_threshold=0.85)
    result = await detector.check("some content")

    assert result.action == "accept"


@pytest.mark.asyncio
async def test_exclude_slug_filters_self(skill_repo, embedder):
    """exclude_slug removes the skill itself from candidates (for amendments)."""
    sid = uuid.uuid4()
    self_summary = _make_summary("my-skill", skill_id=sid)
    other_summary = _make_summary("other-skill", skill_id=uuid.uuid4())

    skill_repo.vector_search_summary.return_value = [self_summary, other_summary]
    # other-skill is very different
    other_skill = _make_full_skill("other-skill", [0.0, 0.0, 1.0], skill_id=other_summary.id)
    skill_repo.get_by_id.return_value = other_skill

    embedder.embed.return_value = [1.0, 0.0, 0.0]

    detector = DuplicateDetector(skill_repo, embedder, reject_threshold=0.95, warn_threshold=0.85)
    result = await detector.check("updated content", exclude_slug="my-skill")

    assert result.action == "accept"
    # Should not have checked the excluded skill
    assert result.most_similar_slug != "my-skill"


@pytest.mark.asyncio
async def test_no_candidates_returns_accept(skill_repo, embedder):
    """When there are no existing skills, result is accept."""
    skill_repo.vector_search_summary.return_value = []

    detector = DuplicateDetector(skill_repo, embedder)
    result = await detector.check("brand new content")

    assert result.action == "accept"
