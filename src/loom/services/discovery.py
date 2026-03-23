"""DiscoveryService: embed queries and rank candidates with constraint awareness."""

import uuid
from typing import TYPE_CHECKING, Any

from cachetools import TTLCache

from loom.models.common import CostProfile, TrustTier
from loom.models.resolution import (
    Alternative,
    RejectedCandidate,
    ResolutionContext,
    ResolutionError,
    ResolvedSkill,
)
from loom.models.skill import SkillSummary

if TYPE_CHECKING:
    from loom.db.repositories.skill_repo import SkillRepo


def _score(skill: SkillSummary, context: ResolutionContext | None) -> float:
    """Compute a ranking score (higher is better)."""
    score = 1.0

    if context is None:
        return score

    # Soft penalise if cost exceeds budget
    if context.cost_budget is not None and not skill.cost_profile.within_budget(
        context.cost_budget
    ):
        score -= 0.5

    return score


class DiscoveryService:
    """Resolves skills from natural-language task descriptions."""

    def __init__(
        self,
        skill_repo: "SkillRepo",
        embedder: Any,
        embed_cache: TTLCache[str, list[float]] | None = None,
    ) -> None:
        self._skill_repo = skill_repo
        self._embedder = embedder
        self._embed_cache: TTLCache[str, list[float]] = embed_cache or TTLCache(
            maxsize=128, ttl=300
        )

    async def _get_embedding(self, text: str) -> list[float]:
        """Return embedding for text, using cache to avoid redundant API calls."""
        cached: list[float] | None = self._embed_cache.get(text)
        if cached is not None:
            return cached
        embed_result = await self._embedder.embed_query(text)
        embedding: list[float] = embed_result.embeddings[0]
        self._embed_cache[text] = embedding
        return embedding

    async def resolve(
        self,
        task_description: str,
        context: ResolutionContext | None = None,
    ) -> ResolvedSkill | ResolutionError:
        """Embed the task, vector-search, apply constraint ranking, return best match."""
        # 1. Embed query (cached)
        query_embedding = await self._get_embedding(task_description)

        # 2. Lightweight vector search — summaries only
        candidates = await self._skill_repo.vector_search_summary(query_embedding, limit=20)

        if not candidates:
            return ResolutionError(
                error="no_match",
                message=f"No skills found matching: {task_description!r}",
            )

        # 3. Apply hard filter: trust floor
        accepted: list[SkillSummary] = []
        rejected: list[RejectedCandidate] = []

        trust_floor = context.trust_floor if context else None
        for skill in candidates:
            if trust_floor is not None and not skill.trust_tier.meets_floor(trust_floor):
                rejected.append(
                    RejectedCandidate(
                        skill=skill,
                        reason=f"Trust tier {skill.trust_tier.value!r} below floor "
                        f"{trust_floor.value!r}",
                    )
                )
            else:
                accepted.append(skill)

        if not accepted:
            return ResolutionError(
                error="no_match",
                message="No skills passed trust floor constraint",
                available_at_lower_tier=candidates,
            )

        # 4. Soft ranking by score
        scored = sorted(
            [(s, _score(s, context)) for s in accepted],
            key=lambda pair: pair[1],
            reverse=True,
        )
        best_summary, _best_score = scored[0]
        rest = scored[1:4]  # top 3 alternatives

        alternatives = [
            Alternative(
                skill=s,
                match_score=score,
                tradeoff="Alternative skill",
            )
            for s, score in rest
        ]

        # 5. Fetch full skill only for the winner
        best = await self._skill_repo.get_by_id(best_summary.id)
        if best is None:
            return ResolutionError(
                error="no_match",
                message=f"Skill {best_summary.slug!r} disappeared during resolution",
            )

        # 6. Build rationale
        rationale = [f"Selected {best.slug!r} as best match"]
        if context and context.cost_budget is not None:
            rationale.append(f"Cost budget: {context.cost_budget.value}")
        if context and context.trust_floor is not None:
            rationale.append(f"Trust floor: {context.trust_floor.value}")

        return ResolvedSkill(
            skill=best,
            alternatives=alternatives,
            rejected_candidates=rejected,
            selection_rationale=rationale,
        )

    async def search(
        self,
        query: str,
        category_id: uuid.UUID | None = None,
        trust_tier: TrustTier | None = None,
        cost_budget: CostProfile | None = None,
    ) -> list[SkillSummary]:
        """Return skill summaries matching query, with optional filters."""
        query_embedding = await self._get_embedding(query)

        candidates = await self._skill_repo.vector_search_summary(
            query_embedding,
            limit=20,
            category_id=category_id,
            trust_tier=trust_tier,
        )

        results = []
        for skill in candidates:
            if cost_budget is not None and not skill.cost_profile.within_budget(cost_budget):
                continue
            results.append(skill)

        return results
