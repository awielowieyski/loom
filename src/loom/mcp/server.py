"""MCP server exposing Loom capability resolution tools."""

import asyncio
import atexit
from typing import Any

from mcp.server.fastmcp import FastMCP

from loom.models.common import CostProfile, TrustTier
from loom.models.resolution import ResolutionContext
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
        "need to do and get back the best matching skill with full instructions.\n"
        "- search(query) — browse available skills by keyword with optional filters.\n"
        "- get_skill(slug) — fetch a specific skill by its identifier.\n"
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
async def resolve(task_description: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Resolve the best skill for a natural-language task description."""
    container = await _get_container()

    resolution_context: ResolutionContext | None = None
    if context is not None:
        resolution_context = ResolutionContext.model_validate(context)

    async with container.pool.acquire() as conn:
        skill_repo = container.skill_repo_factory(conn)
        discovery = container.discovery_service_factory(skill_repo)
        result = await discovery.resolve(task_description, context=resolution_context)
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
async def search(
    query: str,
    category: str | None = None,
    trust_tier: str | None = None,
    cost_budget: str | None = None,
) -> list[dict[str, Any]]:
    """Search skills by query with optional filters."""
    container = await _get_container()

    tier: TrustTier | None = TrustTier(trust_tier) if trust_tier else None
    budget: CostProfile | None = CostProfile(cost_budget) if cost_budget else None

    async with container.pool.acquire() as conn:
        skill_repo = container.skill_repo_factory(conn)
        discovery = container.discovery_service_factory(skill_repo)
        results = await discovery.search(query=query, trust_tier=tier, cost_budget=budget)
    return [s.model_dump() for s in results]


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
