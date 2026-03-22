"""DiscoveryService: embed queries and rank candidates with constraint awareness."""

import uuid
from typing import TYPE_CHECKING, Any

from loom.models.common import CostProfile, TrustTier
from loom.models.resolution import (
    Alternative,
    RejectedCandidate,
    ResolutionContext,
    ResolutionError,
    ResolvedSkill,
)
from loom.models.skill import Skill, SkillSummary

if TYPE_CHECKING:
    from loom.db.repositories.skill_repo import SkillRepo


def _score(skill: Skill, context: ResolutionContext | None) -> float:
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

    def __init__(self, skill_repo: "SkillRepo", embedder: Any) -> None:
        self._skill_repo = skill_repo
        self._embedder = embedder

    async def resolve(
        self,
        task_description: str,
        context: ResolutionContext | None = None,
    ) -> ResolvedSkill | ResolutionError:
        """Embed the task, vector-search, apply constraint ranking, return best match."""
        # 1. Embed query
        embed_result = await self._embedder.embed_query(task_description)
        query_embedding: list[float] = embed_result.embeddings[0]

        # 2. Vector search
        candidates = await self._skill_repo.vector_search(query_embedding, limit=20)

        if not candidates:
            return ResolutionError(
                error="no_match",
                message=f"No skills found matching: {task_description!r}",
            )

        # 3. Apply hard filter: trust floor
        accepted: list[Skill] = []
        rejected: list[RejectedCandidate] = []

        trust_floor = context.trust_floor if context else None
        for skill in candidates:
            if trust_floor is not None and not skill.trust_tier.meets_floor(trust_floor):
                rejected.append(
                    RejectedCandidate(
                        skill=skill.to_summary(),
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
                available_at_lower_tier=[s.to_summary() for s in candidates],
            )

        # 4. Soft ranking by score — compute once, reuse for alternatives
        scored = sorted(
            [(s, _score(s, context)) for s in accepted],
            key=lambda pair: pair[1],
            reverse=True,
        )
        best, _best_score = scored[0]
        rest = scored[1:4]  # top 3 alternatives

        alternatives = [
            Alternative(
                skill=s.to_summary(),
                match_score=score,
                tradeoff="Alternative skill",
            )
            for s, score in rest
        ]

        # 5. Build rationale
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
        embed_result = await self._embedder.embed_query(query)
        query_embedding: list[float] = embed_result.embeddings[0]

        candidates = await self._skill_repo.vector_search(
            query_embedding,
            limit=20,
            category_id=category_id,
            trust_tier=trust_tier,
        )

        results = []
        for skill in candidates:
            if cost_budget is not None and not skill.cost_profile.within_budget(cost_budget):
                continue
            results.append(skill.to_summary())

        return results
