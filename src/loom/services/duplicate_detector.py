"""Embedding similarity check for duplicate skill detection at submission time."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

if TYPE_CHECKING:
    from loom.db.repositories.skill_repo import SkillRepo

logger = logging.getLogger(__name__)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors (pure-python fallback)."""
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(dot / (norm_a * norm_b))


class DuplicateDetectionResult(BaseModel):
    """Result of a duplicate check at submission time."""

    action: str  # "accept", "flag", "reject"
    most_similar_slug: str | None = None
    similarity: float = 0.0
    message: str = ""


class DuplicateDetector:
    """Embedding similarity check at submission time.

    Compares new skill content against existing skills using vector search,
    then applies cosine similarity thresholds to decide whether to accept,
    flag for review, or reject the submission.
    """

    def __init__(
        self,
        skill_repo: SkillRepo,
        embedder: Any,
        reject_threshold: float = 0.95,
        warn_threshold: float = 0.85,
    ) -> None:
        self._skill_repo = skill_repo
        self._embedder = embedder
        self._reject_threshold = reject_threshold
        self._warn_threshold = warn_threshold

    async def check(
        self, content: str, exclude_slug: str | None = None
    ) -> DuplicateDetectionResult:
        """Check if content is a near-duplicate of an existing skill.

        Args:
            content: The skill content to check.
            exclude_slug: Optional slug to exclude from results (for amendments
                checking against themselves).

        Returns:
            DuplicateDetectionResult with action, similarity, and message.
        """
        # Compute embedding for the new content
        embedding = await self._embedder.embed(content)

        # Find the most similar existing skills
        candidates = await self._skill_repo.vector_search_summary(embedding, limit=5)

        # Filter out the excluded slug (self-amendment case)
        if exclude_slug:
            candidates = [c for c in candidates if c.slug != exclude_slug]

        if not candidates:
            return DuplicateDetectionResult(action="accept")

        # Fetch full skill records to get embeddings for precise similarity
        best_sim = 0.0
        best_slug: str | None = None

        for candidate in candidates:
            full_skill = await self._skill_repo.get_by_id(candidate.id)
            if full_skill is None or full_skill.embedding is None:
                continue

            sim = cosine_similarity(embedding, full_skill.embedding)
            if sim > best_sim:
                best_sim = sim
                best_slug = candidate.slug

        if best_sim > self._reject_threshold:
            return DuplicateDetectionResult(
                action="reject",
                most_similar_slug=best_slug,
                similarity=best_sim,
                message=f"Near-duplicate of existing skill '{best_slug}' "
                f"(similarity: {best_sim:.2f})",
            )

        if best_sim > self._warn_threshold:
            return DuplicateDetectionResult(
                action="flag",
                most_similar_slug=best_slug,
                similarity=best_sim,
                message=f"Similar to existing skill '{best_slug}' "
                f"(similarity: {best_sim:.2f}). Review recommended.",
            )

        return DuplicateDetectionResult(
            action="accept",
            most_similar_slug=best_slug,
            similarity=best_sim,
        )
