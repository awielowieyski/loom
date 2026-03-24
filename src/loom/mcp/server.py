"""MCP server exposing Loom capability resolution tools."""

import asyncio
import atexit
import uuid as uuid_mod
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from loom.models.capability import CapabilitySummary
from loom.models.common import CostProfile, TrustTier, UsageOutcome
from loom.models.resolution import ResolutionContext
from loom.models.usage import UsageReportCreate
from loom.services.container import ServiceContainer, close_container, create_container

mcp: FastMCP = FastMCP(
    name="Loom",
    instructions=(
        "Loom provides expert, evaluated skill instructions for tasks you don't have "
        "built-in knowledge for. When asked to do something you're not sure how to "
        "approach — code reviews, documentation, git workflows, testing strategies, "
        "or any unfamiliar task — call resolve() with a natural-language description "
        "of what you need to accomplish. It returns step-by-step instructions you "
        "should follow to complete the task.\n\n"
        "Tools:\n"
        "- resolve(task_description) — your primary entry point. Describe what you "
        "need to do and get back the best matching skill or capability with full "
        "instructions. Use type='any' (default) to search both, or 'skill'/'capability' "
        "to narrow.\n"
        "- resolve_capability(task_description) — resolve a multi-step capability "
        "(execution plan) specifically.\n"
        "- search(query) — browse available skills and capabilities by keyword with "
        "optional filters.\n"
        "- get_skill(slug) — fetch a specific skill by its identifier.\n"
        "- get_capability(slug) — fetch a specific capability by its identifier.\n"
        "- list_categories() — explore what kinds of skills are available."
    ),
)

_container: ServiceContainer | None = None


async def _get_container() -> ServiceContainer:
    """Lazy-initialise the shared container on first call."""
    global _container  # noqa: PLW0603
    if _container is None:
        from loom.settings import LoomSettings

        settings = LoomSettings()
        _container = await create_container(settings)
    return _container


async def _shutdown() -> None:
    """Close pool on shutdown."""
    global _container  # noqa: PLW0603
    if _container is not None:
        await close_container(_container)
        _container = None


@mcp.tool()
async def resolve(
    task_description: str,
    context: dict[str, Any] | None = None,
    type: Literal["any", "skill", "capability"] = "any",
) -> dict[str, Any]:
    """Resolve the best skill for a natural-language task description.

    Use type='any' (default) to search both skills and capabilities,
    'skill' for skills only, or 'capability' for capabilities only.
    """
    container = await _get_container()

    resolution_context: ResolutionContext | None = None
    if context is not None:
        resolution_context = ResolutionContext.model_validate(context)

    async with container.pool.acquire() as conn:
        skill_repo = container.skill_repo_factory(conn)

        if type == "skill":
            # Skill-only: use original DiscoveryService
            discovery = container.discovery_service_factory(skill_repo)
            skill_result = await discovery.resolve(task_description, context=resolution_context)
            result = skill_result.model_dump()
        else:
            # "any" or "capability": use UnifiedResolver
            capability_repo = container.capability_repo_factory(conn)
            unified = container.unified_resolver_factory(skill_repo, capability_repo)
            unified_result = await unified.resolve(
                task_description, context=resolution_context, type_filter=type
            )
            result = unified_result.model_dump()

        # Enrich with M4 fields if a skill was resolved
        skill_data = result.get("skill")
        slug = skill_data.get("slug") if isinstance(skill_data, dict) else None
        if slug:
            skill = await skill_repo.get_by_slug(slug)
            if skill is not None:
                await skill_repo.increment_resolution_count(skill.id)
                result["deprecated"] = skill.deprecated_at is not None
                result["successor"] = (
                    {"slug": skill.successor_slug} if skill.successor_slug else None
                )
                result["stale"] = skill.stale_since is not None
                result["behavioral_score"] = skill.behavioral_score

                # Fetch 30d usage success rate if available
                usage_repo = container.usage_repo_factory(conn)
                agg = await usage_repo.get_aggregate_for_skill(skill.id, "30d")
                result["usage_success_rate"] = agg.success_rate if agg else None

    return result


@mcp.tool()
async def report_usage(
    skill_slug: str,
    skill_version: str,
    outcome: str,
    runtime_ms: int | None = None,
    context_hash: str | None = None,
    failure_reason: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Report usage outcome for a skill. Same semantics as the REST endpoint."""
    container = await _get_container()

    if idempotency_key is None:
        idempotency_key = str(uuid_mod.uuid4())

    report = UsageReportCreate(
        skill_slug=skill_slug,
        skill_version=skill_version,
        outcome=UsageOutcome(outcome),
        runtime_ms=runtime_ms,
        context_hash=context_hash,
        failure_reason=failure_reason,
        idempotency_key=idempotency_key,
    )

    async with container.pool.acquire() as conn:
        usage_repo = container.usage_repo_factory(conn)
        skill_repo = container.skill_repo_factory(conn)
        svc = container.usage_service_factory(usage_repo, skill_repo)
        try:
            result = await svc.report_usage(report)
        except ValueError as exc:
            return {"error": "not_found", "message": str(exc)}

    return result.model_dump()


@mcp.tool()
async def resolve_capability(
    task_description: str, context: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Resolve the best capability (multi-step execution plan) for a task."""
    container = await _get_container()

    resolution_context: ResolutionContext | None = None
    if context is not None:
        resolution_context = ResolutionContext.model_validate(context)

    async with container.pool.acquire() as conn:
        capability_repo = container.capability_repo_factory(conn)
        skill_repo = container.skill_repo_factory(conn)
        cap_discovery = container.capability_discovery_factory(capability_repo, skill_repo)
        result = await cap_discovery.resolve(task_description, context=resolution_context)
    return result.model_dump()


@mcp.tool()
async def get_skill(slug: str, version: str | None = None) -> dict[str, Any]:
    """Retrieve a skill by slug and optional version."""
    container = await _get_container()

    async with container.pool.acquire() as conn:
        skill_repo = container.skill_repo_factory(conn)
        category_repo = container.category_repo_factory(conn)
        registry = container.registry_service_factory(skill_repo, category_repo)
        skill = await registry.get_skill(slug, version=version)

    if skill is None:
        return {"error": "not_found", "message": f"Skill {slug!r} not found"}
    return skill.model_dump()


@mcp.tool()
async def get_capability(slug: str, version: str | None = None) -> dict[str, Any]:
    """Retrieve a capability by slug and optional version."""
    container = await _get_container()

    async with container.pool.acquire() as conn:
        capability_repo = container.capability_repo_factory(conn)
        category_repo = container.category_repo_factory(conn)
        cap_registry = container.capability_registry_factory(capability_repo, category_repo)
        capability = await cap_registry.get_capability(slug, version=version)

    if capability is None:
        return {"error": "not_found", "message": f"Capability {slug!r} not found"}
    return capability.model_dump()


@mcp.tool()
async def search(
    query: str,
    category: str | None = None,
    trust_tier: str | None = None,
    cost_budget: str | None = None,
    type: Literal["any", "skill", "capability"] = "any",
) -> list[dict[str, Any]]:
    """Search skills by query with optional filters.

    Use type='any' (default) to search both skills and capabilities,
    'skill' for skills only, or 'capability' for capabilities only.
    """
    container = await _get_container()

    tier: TrustTier | None = TrustTier(trust_tier) if trust_tier else None
    budget: CostProfile | None = CostProfile(cost_budget) if cost_budget else None

    async with container.pool.acquire() as conn:
        skill_repo = container.skill_repo_factory(conn)

        if type == "skill":
            discovery = container.discovery_service_factory(skill_repo)
            skill_results = await discovery.search(query=query, trust_tier=tier, cost_budget=budget)
            return [s.model_dump() for s in skill_results]

        # "any" or "capability": use UnifiedResolver
        capability_repo = container.capability_repo_factory(conn)
        unified = container.unified_resolver_factory(skill_repo, capability_repo)
        unified_results = await unified.search(
            query=query, trust_tier=tier, cost_budget=budget, type_filter=type
        )
    return [
        {**s.model_dump(), "type": "capability" if isinstance(s, CapabilitySummary) else "skill"}
        for s in unified_results
    ]


@mcp.tool()
async def list_categories() -> list[dict[str, Any]]:
    """List all skill categories."""
    container = await _get_container()

    async with container.pool.acquire() as conn:
        category_repo = container.category_repo_factory(conn)
        categories = await category_repo.list_all()
    return [c.model_dump() for c in categories]


def main() -> None:
    """Run the MCP server."""
    from loom.settings import LoomSettings

    settings = LoomSettings()
    transport = settings.mcp.transports[0].type if settings.mcp.transports else "stdio"

    # Register cleanup for pool on exit
    def _cleanup() -> None:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(_shutdown())
            else:
                loop.run_until_complete(_shutdown())
        except RuntimeError:
            pass

    atexit.register(_cleanup)
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
