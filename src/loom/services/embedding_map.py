"""Service for computing 2D embedding map projections via UMAP."""

from __future__ import annotations

import asyncio
import random
import time
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    import asyncpg


# Cache TTL in seconds (1 hour)
_CACHE_TTL = 3600


class EmbeddingMapService:
    """Computes and caches a 2D UMAP projection of skill/capability embeddings."""

    _cache: dict[str, Any] = {}
    _cache_ts: float = 0.0

    def __init__(self) -> None:
        # Instance-level cache so tests can get fresh instances
        self._cache: dict[str, Any] = {}
        self._cache_ts: float = 0.0

    async def compute_map(self, conn: asyncpg.Connection) -> dict[str, list[dict[str, Any]]]:
        """Return projected embedding map data, using cache if fresh."""
        now = time.monotonic()
        if self._cache and (now - self._cache_ts) < _CACHE_TTL:
            return self._cache

        result = await self._build_map(conn)
        self._cache = result
        self._cache_ts = time.monotonic()
        return result

    async def _build_map(self, conn: asyncpg.Connection) -> dict[str, list[dict[str, Any]]]:
        """Fetch embeddings, project to 2D, and assemble response."""
        # Fetch skills with embeddings
        skill_rows = await conn.fetch(
            """
            SELECT s.slug, s.name, s.trust_tier, s.composite_score, s.behavioral_score,
                   s.embedding, c.slug AS category_slug
            FROM skills s
            LEFT JOIN categories c ON s.category_id = c.id
            WHERE s.embedding IS NOT NULL
            """
        )

        # Fetch capabilities with embeddings
        cap_rows = await conn.fetch(
            """
            SELECT cap.slug, cap.name, cap.trust_tier, cap.composite_score,
                   cap.embedding, cap.steps, c.slug AS category_slug
            FROM capabilities cap
            LEFT JOIN categories c ON cap.category_id = c.id
            WHERE cap.embedding IS NOT NULL
            """
        )

        total = len(skill_rows) + len(cap_rows)

        if total == 0:
            return {"skills": [], "capabilities": []}

        # Collect all embeddings for UMAP
        embeddings: list[np.ndarray] = []
        for row in skill_rows:
            embeddings.append(np.array(row["embedding"], dtype=np.float32))
        for row in cap_rows:
            embeddings.append(np.array(row["embedding"], dtype=np.float32))

        embedding_matrix = np.vstack(embeddings)

        # Project to 2D
        if total < 5:
            coords = _random_layout(total)
        else:
            loop = asyncio.get_event_loop()
            coords = await loop.run_in_executor(None, _run_umap, embedding_matrix)

        # Build response
        skills: list[dict[str, Any]] = []
        for i, row in enumerate(skill_rows):
            skills.append(
                {
                    "slug": row["slug"],
                    "name": row["name"],
                    "x": float(coords[i, 0]),
                    "y": float(coords[i, 1]),
                    "trust_tier": row["trust_tier"],
                    "category": row["category_slug"] or "uncategorized",
                    "composite_score": _to_float(row["composite_score"]),
                    "behavioral_score": _to_float(row["behavioral_score"]),
                }
            )

        capabilities: list[dict[str, Any]] = []
        offset = len(skill_rows)
        for j, row in enumerate(cap_rows):
            step_slugs = _extract_step_slugs(row["steps"])
            capabilities.append(
                {
                    "slug": row["slug"],
                    "name": row["name"],
                    "x": float(coords[offset + j, 0]),
                    "y": float(coords[offset + j, 1]),
                    "trust_tier": row["trust_tier"],
                    "category": row["category_slug"] or "uncategorized",
                    "composite_score": _to_float(row["composite_score"]),
                    "step_slugs": step_slugs,
                }
            )

        return {"skills": skills, "capabilities": capabilities}


def _random_layout(n: int) -> np.ndarray:
    """Generate random 2D coordinates in [-1, 1] for small datasets."""
    rng = random.Random(42)
    return np.array([[rng.uniform(-1, 1), rng.uniform(-1, 1)] for _ in range(n)])


def _run_umap(embedding_matrix: np.ndarray) -> np.ndarray:
    """Run UMAP dimensionality reduction (blocking — intended for executor)."""
    import umap

    reducer = umap.UMAP(n_components=2, n_neighbors=15, min_dist=0.1, random_state=42)
    projected = reducer.fit_transform(embedding_matrix)
    # Normalise to [-1, 1]
    mins = projected.min(axis=0)
    maxs = projected.max(axis=0)
    ranges = maxs - mins
    ranges[ranges == 0] = 1.0  # avoid division by zero
    normalised = 2.0 * (projected - mins) / ranges - 1.0
    return normalised  # type: ignore[no-any-return]


def _to_float(val: Any) -> float | None:
    """Convert a value to float or None."""
    if val is None:
        return None
    return float(val)


def _extract_step_slugs(steps: list[dict[str, Any]] | None) -> list[str]:
    """Extract skill_ref slugs from capability steps."""
    if not steps:
        return []
    return [s["skill_ref"] for s in steps if "skill_ref" in s]
