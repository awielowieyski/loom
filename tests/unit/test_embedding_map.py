"""Tests for EmbeddingMapService."""

import numpy as np
import pytest

from loom.services.embedding_map import EmbeddingMapService, _random_layout, _run_umap


def _make_conn_mock(skill_rows, cap_rows):
    """Create an async mock connection that returns provided rows."""
    from unittest.mock import AsyncMock

    conn = AsyncMock()
    conn.fetch = AsyncMock(side_effect=[skill_rows, cap_rows])
    return conn


def _make_skill_row(
    slug: str = "test-skill",
    name: str = "Test Skill",
    trust_tier: str = "community",
    composite_score: float | None = 0.82,
    behavioral_score: float | None = 0.85,
    category_slug: str = "documentation",
    embedding_dim: int = 1536,
) -> dict:
    rng = np.random.default_rng(hash(slug) % (2**31))
    return {
        "slug": slug,
        "name": name,
        "trust_tier": trust_tier,
        "composite_score": composite_score,
        "behavioral_score": behavioral_score,
        "category_slug": category_slug,
        "embedding": rng.standard_normal(embedding_dim).astype(np.float32).tolist(),
    }


def _make_cap_row(
    slug: str = "test-cap",
    name: str = "Test Capability",
    trust_tier: str = "community",
    composite_score: float | None = 0.78,
    category_slug: str = "development/review",
    step_slugs: list[str] | None = None,
    embedding_dim: int = 1536,
) -> dict:
    rng = np.random.default_rng(hash(slug) % (2**31))
    steps = [{"skill_ref": s, "role": "step"} for s in (step_slugs or ["s1", "s2"])]
    return {
        "slug": slug,
        "name": name,
        "trust_tier": trust_tier,
        "composite_score": composite_score,
        "category_slug": category_slug,
        "steps": steps,
        "embedding": rng.standard_normal(embedding_dim).astype(np.float32).tolist(),
    }


@pytest.mark.asyncio
async def test_empty_registry():
    """Empty registry returns empty lists."""
    conn = _make_conn_mock([], [])
    svc = EmbeddingMapService()
    result = await svc.compute_map(conn)
    assert result == {"skills": [], "capabilities": []}


@pytest.mark.asyncio
async def test_few_items_uses_random_layout():
    """Fewer than 5 items total triggers random layout instead of UMAP."""
    skills = [_make_skill_row(slug=f"s{i}") for i in range(2)]
    caps = [_make_cap_row(slug=f"c{i}") for i in range(1)]
    conn = _make_conn_mock(skills, caps)
    svc = EmbeddingMapService()
    result = await svc.compute_map(conn)

    assert len(result["skills"]) == 2
    assert len(result["capabilities"]) == 1

    # Coordinates should be in [-1, 1] range
    for s in result["skills"]:
        assert -1.0 <= s["x"] <= 1.0
        assert -1.0 <= s["y"] <= 1.0
    for c in result["capabilities"]:
        assert -1.0 <= c["x"] <= 1.0
        assert -1.0 <= c["y"] <= 1.0


@pytest.mark.asyncio
async def test_enough_items_uses_umap():
    """With 5+ items, UMAP is used for projection."""
    skills = [_make_skill_row(slug=f"s{i}", embedding_dim=384) for i in range(4)]
    caps = [_make_cap_row(slug=f"c{i}", embedding_dim=384) for i in range(2)]
    conn = _make_conn_mock(skills, caps)
    svc = EmbeddingMapService()
    result = await svc.compute_map(conn)

    assert len(result["skills"]) == 4
    assert len(result["capabilities"]) == 2

    # UMAP output should be normalised to [-1, 1]
    for s in result["skills"]:
        assert -1.0 <= s["x"] <= 1.0
        assert -1.0 <= s["y"] <= 1.0

    # Check metadata fields
    s0 = result["skills"][0]
    assert "slug" in s0
    assert "trust_tier" in s0
    assert "composite_score" in s0
    assert "behavioral_score" in s0
    assert "category" in s0

    c0 = result["capabilities"][0]
    assert "step_slugs" in c0
    assert isinstance(c0["step_slugs"], list)


@pytest.mark.asyncio
async def test_cache_hit():
    """Second call should return cached result without querying DB again."""
    from unittest.mock import AsyncMock

    skills = [_make_skill_row(slug=f"s{i}") for i in range(2)]
    conn = _make_conn_mock(skills, [])
    svc = EmbeddingMapService()

    result1 = await svc.compute_map(conn)
    assert len(result1["skills"]) == 2

    # Second call with a fresh mock — should NOT be called
    conn2 = AsyncMock()
    conn2.fetch = AsyncMock(side_effect=AssertionError("Should not query DB on cache hit"))
    result2 = await svc.compute_map(conn2)

    assert result1 is result2


@pytest.mark.asyncio
async def test_null_scores():
    """Null composite/behavioral scores are preserved as None."""
    skills = [_make_skill_row(slug="s1", composite_score=None, behavioral_score=None)]
    conn = _make_conn_mock(skills, [])
    svc = EmbeddingMapService()
    result = await svc.compute_map(conn)

    assert result["skills"][0]["composite_score"] is None
    assert result["skills"][0]["behavioral_score"] is None


@pytest.mark.asyncio
async def test_queries_only_include_published_rows():
    conn = _make_conn_mock([], [])
    svc = EmbeddingMapService()

    await svc.compute_map(conn)

    assert conn.fetch.await_count == 2
    for call in conn.fetch.await_args_list:
        sql = call.args[0]
        assert "lifecycle_state = 'published'" in sql


def test_random_layout_shape():
    """Random layout returns correct shape."""
    coords = _random_layout(7)
    assert coords.shape == (7, 2)
    assert np.all(coords >= -1.0)
    assert np.all(coords <= 1.0)


def test_run_umap_normalised():
    """UMAP output should be normalised to [-1, 1]."""
    rng = np.random.default_rng(0)
    matrix = rng.standard_normal((20, 128)).astype(np.float32)
    coords = _run_umap(matrix)
    assert coords.shape == (20, 2)
    assert np.all(coords >= -1.0 - 1e-6)
    assert np.all(coords <= 1.0 + 1e-6)
