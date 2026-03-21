"""MCP server exposing Loom capability resolution tools."""

from typing import Any

from mcp.server.fastmcp import FastMCP

from loom.db.repositories.category_repo import CategoryRepo
from loom.db.repositories.skill_repo import SkillRepo
from loom.models.common import CostProfile, TrustTier
from loom.models.resolution import ResolutionContext
from loom.services.discovery import DiscoveryService
from loom.services.registry import RegistryService

mcp: FastMCP = FastMCP(
    name="Loom",
    instructions=(
        "Loom is a capability resolution service for agents. "
        "Use resolve() to find the best skill for a task, "
        "get_skill() to fetch a specific skill, "
        "search() to list matching skills, "
        "and list_categories() to explore the skill taxonomy."
    ),
)

_services: dict[str, Any] = {}


async def _get_services() -> dict[str, Any]:
    """Lazy-initialise shared services on first call."""
    if not _services:
        from loom.db.engine import create_pool
        from loom.providers.embeddings import create_embedder
        from loom.settings import LoomSettings

        settings = LoomSettings()
        pool = await create_pool(settings.database.url)
        embedder = create_embedder(settings.embedding)

        conn = await pool.acquire()
        skill_repo = SkillRepo(conn)
        category_repo = CategoryRepo(conn)
        discovery = DiscoveryService(skill_repo=skill_repo, embedder=embedder)
        registry = RegistryService(
            skill_repo=skill_repo,
            category_repo=category_repo,
            eval_service=None,  # type: ignore[arg-type]
        )
        _services["pool"] = pool
        _services["conn"] = conn
        _services["discovery"] = discovery
        _services["registry"] = registry
        _services["category_repo"] = category_repo

    return _services


@mcp.tool()  # type: ignore[misc]
async def resolve(task_description: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Resolve the best skill for a natural-language task description."""
    services = await _get_services()
    discovery: DiscoveryService = services["discovery"]

    resolution_context: ResolutionContext | None = None
    if context is not None:
        resolution_context = ResolutionContext.model_validate(context)

    result = await discovery.resolve(task_description, context=resolution_context)
    return result.model_dump()


@mcp.tool()  # type: ignore[misc]
async def get_skill(slug: str, version: str | None = None) -> dict[str, Any]:
    """Retrieve a skill by slug and optional version."""
    services = await _get_services()
    registry: RegistryService = services["registry"]

    skill = await registry.get_skill(slug, version=version)
    if skill is None:
        return {"error": "not_found", "message": f"Skill {slug!r} not found"}
    return skill.model_dump()


@mcp.tool()  # type: ignore[misc]
async def search(
    query: str,
    category: str | None = None,
    trust_tier: str | None = None,
    cost_budget: str | None = None,
) -> list[dict[str, Any]]:
    """Search skills by query with optional filters."""
    services = await _get_services()
    discovery: DiscoveryService = services["discovery"]

    tier: TrustTier | None = TrustTier(trust_tier) if trust_tier else None
    budget: CostProfile | None = CostProfile(cost_budget) if cost_budget else None

    results = await discovery.search(query=query, trust_tier=tier, cost_budget=budget)
    return [s.model_dump() for s in results]


@mcp.tool()  # type: ignore[misc]
async def list_categories() -> list[dict[str, Any]]:
    """List all skill categories."""
    services = await _get_services()
    category_repo: CategoryRepo = services["category_repo"]

    categories = await category_repo.list_all()
    return [c.model_dump() for c in categories]


def main() -> None:
    """Run the MCP server."""
    from loom.settings import LoomSettings

    settings = LoomSettings()
    transport = settings.mcp.transports[0].type if settings.mcp.transports else "stdio"
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
