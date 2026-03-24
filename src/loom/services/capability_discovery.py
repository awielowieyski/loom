"""CapabilityDiscoveryService: resolve capabilities from natural-language queries."""

import asyncio
import uuid
from typing import TYPE_CHECKING, Any

from cachetools import TTLCache

from loom.extends.resolver import ExtendsResolver
from loom.models.common import CostProfile, TrustTier
from loom.models.resolution import (
    Alternative,
    RejectedCandidate,
    ResolutionContext,
    ResolutionError,
    ResolvedCapability,
    ResolvedStep,
)
from loom.models.skill import Skill, SkillSummary

if TYPE_CHECKING:
    from loom.db.repositories.capability_repo import CapabilityRepo
    from loom.db.repositories.skill_repo import SkillRepo
    from loom.models.capability import CapabilityStep, CapabilitySummary


def _score(cap: "CapabilitySummary", context: ResolutionContext | None) -> float:
    """Compute a ranking score (higher is better)."""
    score = 1.0
    if context is None:
        return score
    if context.cost_budget is not None and not cap.cost_profile.within_budget(context.cost_budget):
        score -= 0.5
    return score


_extends_resolver = ExtendsResolver()


class CapabilityDiscoveryService:
    """Resolves capabilities from natural-language task descriptions."""

    def __init__(
        self,
        capability_repo: "CapabilityRepo",
        skill_repo: "SkillRepo",
        embedder: Any,
        embed_cache: TTLCache[str, list[float]] | None = None,
    ) -> None:
        self._capability_repo = capability_repo
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

    async def _resolve_step_skill(self, step: "CapabilityStep") -> Skill | None:
        """Resolve a step's skill_ref to a full Skill object."""
        source, slug, version = _extends_resolver.parse_extends_uri(step.skill_ref)

        if source == "corp":
            # Corporate skills are not available in public context — create placeholder
            return Skill(
                id=uuid.uuid4(),
                slug=slug,
                name=slug,
                description=f"Corporate skill: {slug}",
                content="Corporate skill not available in public context",
                category_id=uuid.uuid4(),
                tags=[],
                scope="corporate",
                version=version or "0.0.0",
                author_id=uuid.uuid4(),
                trust_tier=TrustTier.COMMUNITY,
                cost_profile=CostProfile.FREE,
                cost_drivers=[],
                estimated_duration="fast",
            )

        return await self._skill_repo.get_by_slug(slug, version=version)

    def _compute_step_deps(
        self, skill: Skill, available_tools: list[str]
    ) -> tuple[list[str], list[str]]:
        """Compute satisfied and missing dependencies for a skill against available tools."""
        satisfied: list[str] = []
        missing: list[str] = []

        for mcp in skill.dependencies.mcp_servers:
            if mcp.uri in available_tools:
                satisfied.append(mcp.uri)
            else:
                missing.append(mcp.uri)

        for api in skill.dependencies.apis:
            if api.name in available_tools:
                satisfied.append(api.name)
            else:
                missing.append(api.name)

        return satisfied, missing

    async def resolve(
        self,
        task_description: str,
        context: ResolutionContext | None = None,
    ) -> ResolvedCapability | ResolutionError:
        """Embed the task, vector-search capabilities, resolve steps, return best match."""
        # 1. Embed query (cached)
        query_embedding = await self._get_embedding(task_description)

        # 2. Lightweight vector search — summaries only
        candidates = await self._capability_repo.vector_search_summary(query_embedding, limit=20)

        if not candidates:
            return ResolutionError(
                error="no_match",
                message=f"No capabilities found matching: {task_description!r}",
            )

        # 3. Apply hard filter: trust floor
        accepted: list[CapabilitySummary] = []
        rejected: list[RejectedCandidate] = []

        trust_floor = context.trust_floor if context else None
        for cap in candidates:
            if trust_floor is not None and not cap.trust_tier.meets_floor(trust_floor):
                # Create a SkillSummary-like object for rejected tracking
                rejected.append(
                    RejectedCandidate(
                        skill=SkillSummary(
                            id=cap.id,
                            slug=cap.slug,
                            name=cap.name,
                            description=cap.description,
                            category_id=cap.category_id,
                            tags=cap.tags,
                            version=cap.version,
                            trust_tier=cap.trust_tier,
                            cost_profile=cap.cost_profile,
                            estimated_duration=cap.estimated_duration,
                        ),
                        reason=f"Trust tier {cap.trust_tier.value!r} below floor "
                        f"{trust_floor.value!r}",
                    )
                )
            else:
                accepted.append(cap)

        if not accepted:
            return ResolutionError(
                error="no_match",
                message="No capabilities passed trust floor constraint",
            )

        # 4. Soft ranking by score
        scored = sorted(
            [(c, _score(c, context)) for c in accepted],
            key=lambda pair: pair[1],
            reverse=True,
        )
        best_summary, _best_score = scored[0]
        rest = scored[1:4]

        alternatives = [
            Alternative(
                skill=SkillSummary(
                    id=c.id,
                    slug=c.slug,
                    name=c.name,
                    description=c.description,
                    category_id=c.category_id,
                    tags=c.tags,
                    version=c.version,
                    trust_tier=c.trust_tier,
                    cost_profile=c.cost_profile,
                    estimated_duration=c.estimated_duration,
                ),
                match_score=s,
                tradeoff="Alternative capability",
            )
            for c, s in rest
        ]

        # 5. Fetch full capability for the winner
        best = await self._capability_repo.get_by_id(best_summary.id)
        if best is None:
            return ResolutionError(
                error="no_match",
                message=f"Capability {best_summary.slug!r} disappeared during resolution",
            )

        # 6. Resolve each step's skill
        available_tools = context.available_tools if context else []
        resolved_steps: list[ResolvedStep] = []
        all_satisfied: list[str] = []
        all_missing: list[str] = []
        step_trust_tiers: list[TrustTier] = []
        trust_warnings: list[str] = []

        # Resolve all step skills in parallel
        skills = await asyncio.gather(*[self._resolve_step_skill(step) for step in best.steps])

        for idx, (step, skill) in enumerate(zip(best.steps, skills, strict=True)):
            if skill is None:
                return ResolutionError(
                    error="step_resolution_failed",
                    message=f"Could not resolve skill for step {idx}: {step.skill_ref!r}",
                )

            step_trust_tiers.append(skill.trust_tier)
            satisfied, missing = self._compute_step_deps(skill, available_tools)
            all_satisfied.extend(satisfied)
            all_missing.extend(missing)

            resolved_steps.append(
                ResolvedStep(
                    index=idx,
                    skill_ref=step.skill_ref,
                    role=step.role,
                    skill=skill,
                    inputs=step.inputs,
                    outputs=step.outputs,
                    required=step.required,
                    data_classification=step.data_classification,
                    dependencies_satisfied=satisfied,
                    dependencies_missing=missing,
                )
            )

            # Trust warning for experimental skills
            if skill.trust_tier == TrustTier.EXPERIMENTAL:
                trust_warnings.append(f"Step {idx} ({skill.slug}) uses an experimental skill")

        # 7. Compute effective trust tier = min across all step skills
        if step_trust_tiers:
            effective_trust = min(step_trust_tiers, key=lambda t: t.rank)
        else:
            effective_trust = best.trust_tier

        # Re-check effective trust against trust floor
        if trust_floor is not None and not effective_trust.meets_floor(trust_floor):
            return ResolutionError(
                error="no_match",
                message=(
                    f"Capability {best.slug!r} effective trust tier "
                    f"{effective_trust.value!r} (from step skills) below floor "
                    f"{trust_floor.value!r}"
                ),
            )

        # 8. Build rationale
        rationale = [f"Selected {best.slug!r} as best match"]
        if context and context.cost_budget is not None:
            rationale.append(f"Cost budget: {context.cost_budget.value}")
        if context and context.trust_floor is not None:
            rationale.append(f"Trust floor: {context.trust_floor.value}")

        # Data flow safety warnings
        for edge in best.data_flow:
            if edge.classification == "external":
                rationale.append(
                    f"Step {edge.to_step!r} consumes external data from step "
                    f"{edge.from_step!r}; treat inputs as untrusted."
                )

        # Deduplicate aggregated deps
        all_satisfied_dedup = list(dict.fromkeys(all_satisfied))
        all_missing_dedup = list(dict.fromkeys(all_missing))

        return ResolvedCapability(
            capability=best,
            resolved_steps=resolved_steps,
            effective_trust_tier=effective_trust,
            trust_warnings=trust_warnings,
            all_dependencies_satisfied=all_satisfied_dedup,
            all_dependencies_missing=all_missing_dedup,
            data_flow=best.data_flow,
            alternatives=alternatives,
            selection_rationale=rationale,
        )

    async def search(
        self,
        query: str,
        category_id: uuid.UUID | None = None,
        trust_tier: TrustTier | None = None,
        cost_budget: CostProfile | None = None,
    ) -> list["CapabilitySummary"]:
        """Return capability summaries matching query, with optional filters."""
        query_embedding = await self._get_embedding(query)

        candidates = await self._capability_repo.vector_search_summary(
            query_embedding,
            limit=20,
            category_id=category_id,
            trust_tier=trust_tier,
        )

        results = []
        for cap in candidates:
            if cost_budget is not None and not cap.cost_profile.within_budget(cost_budget):
                continue
            results.append(cap)

        return results
