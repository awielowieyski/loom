"""UnifiedResolver: resolve either skills or capabilities from a single entry point."""

import uuid
from typing import TYPE_CHECKING, Literal

from loom.models.common import CostProfile, TrustTier
from loom.models.resolution import (
    ResolutionContext,
    ResolutionError,
    ResolvedCapability,
    ResolvedResult,
    ResolvedSkill,
)

if TYPE_CHECKING:
    from loom.models.capability import CapabilitySummary
    from loom.models.skill import SkillSummary
    from loom.services.capability_discovery import CapabilityDiscoveryService
    from loom.services.discovery import DiscoveryService


class UnifiedResolver:
    """Resolves either skills or capabilities, picking the best match."""

    def __init__(
        self,
        discovery_service: "DiscoveryService",
        capability_discovery_service: "CapabilityDiscoveryService",
    ) -> None:
        self._skill_service = discovery_service
        self._capability_service = capability_discovery_service

    async def resolve(
        self,
        task_description: str,
        context: ResolutionContext | None = None,
        type_filter: Literal["any", "skill", "capability"] = "any",
    ) -> ResolvedResult | ResolutionError:
        """Resolve a task description to either a skill or capability.

        When type_filter is "any", both services are queried and the
        best match is returned based on the number of selection rationale
        entries (a proxy for match confidence).
        """
        skill_result: ResolvedSkill | ResolutionError | None = None
        cap_result: ResolvedCapability | ResolutionError | None = None

        if type_filter in ("skill", "any"):
            skill_result = await self._skill_service.resolve(task_description, context=context)

        if type_filter in ("capability", "any"):
            cap_result = await self._capability_service.resolve(task_description, context=context)

        # Determine winners
        skill_ok = isinstance(skill_result, ResolvedSkill)
        cap_ok = isinstance(cap_result, ResolvedCapability)

        if skill_ok and cap_ok:
            # Both matched — compare: prefer skill for simplicity unless
            # capability has more rationale entries (indicating richer match)
            assert isinstance(skill_result, ResolvedSkill)
            assert isinstance(cap_result, ResolvedCapability)
            skill_score = len(skill_result.selection_rationale)
            cap_score = len(cap_result.selection_rationale)
            if cap_score > skill_score:
                return ResolvedResult(type="capability", capability=cap_result)
            return ResolvedResult(type="skill", skill=skill_result)

        if skill_ok:
            assert isinstance(skill_result, ResolvedSkill)
            return ResolvedResult(type="skill", skill=skill_result)

        if cap_ok:
            assert isinstance(cap_result, ResolvedCapability)
            return ResolvedResult(type="capability", capability=cap_result)

        # Neither matched — return the most informative error
        if isinstance(skill_result, ResolutionError):
            return skill_result
        if isinstance(cap_result, ResolutionError):
            return cap_result

        return ResolutionError(
            error="no_match",
            message=f"No skills or capabilities found matching: {task_description!r}",
        )

    async def search(
        self,
        query: str,
        type_filter: Literal["any", "skill", "capability"] = "any",
        category_id: uuid.UUID | None = None,
        trust_tier: TrustTier | None = None,
        cost_budget: CostProfile | None = None,
    ) -> list["SkillSummary | CapabilitySummary"]:
        """Search across both skills and capabilities."""
        results: list[SkillSummary | CapabilitySummary] = []

        if type_filter in ("skill", "any"):
            skills = await self._skill_service.search(
                query,
                category_id=category_id,
                trust_tier=trust_tier,
                cost_budget=cost_budget,
            )
            results.extend(skills)

        if type_filter in ("capability", "any"):
            caps = await self._capability_service.search(
                query,
                category_id=category_id,
                trust_tier=trust_tier,
                cost_budget=cost_budget,
            )
            results.extend(caps)

        return results
