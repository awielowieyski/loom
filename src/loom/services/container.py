"""Shared service container — single place to wire up DB pool, embedder, and repo factories."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from cachetools import TTLCache

from loom.db.repositories.category_repo import CategoryRepo
from loom.db.repositories.skill_repo import SkillRepo
from loom.services.discovery import DiscoveryService
from loom.services.eval import EvalService
from loom.services.registry import RegistryService

if TYPE_CHECKING:
    from collections.abc import Callable

    import asyncpg


@dataclass(frozen=True, slots=True)
class ServiceContainer:
    """Holds shared infrastructure and factories for building per-request services."""

    pool: asyncpg.Pool
    settings: object  # LoomSettings — kept as object to avoid circular import
    embedder: object  # Embedder instance

    # Factories: each takes a connection and returns a repo / service
    skill_repo_factory: Callable[[asyncpg.Connection], SkillRepo]
    category_repo_factory: Callable[[asyncpg.Connection], CategoryRepo]
    registry_service_factory: Callable[[SkillRepo, CategoryRepo], RegistryService]
    discovery_service_factory: Callable[[SkillRepo], DiscoveryService]


async def create_container(settings: object) -> ServiceContainer:
    """Build a fully-wired container from settings."""
    from loom.db.engine import create_pool
    from loom.providers.embeddings import create_embedder
    from loom.settings import LoomSettings

    assert isinstance(settings, LoomSettings)
    pool = await create_pool(settings.database.url)
    embedder = create_embedder(settings.embedding)
    eval_service = EvalService()
    embed_cache: TTLCache[str, list[float]] = TTLCache(maxsize=128, ttl=300)

    def _skill_repo(conn: asyncpg.Connection) -> SkillRepo:
        return SkillRepo(conn)

    def _category_repo(conn: asyncpg.Connection) -> CategoryRepo:
        return CategoryRepo(conn)

    def _registry(skill_repo: SkillRepo, category_repo: CategoryRepo) -> RegistryService:
        return RegistryService(
            skill_repo=skill_repo,
            category_repo=category_repo,
            eval_service=eval_service,
        )

    def _discovery(skill_repo: SkillRepo) -> DiscoveryService:
        return DiscoveryService(skill_repo=skill_repo, embedder=embedder, embed_cache=embed_cache)

    return ServiceContainer(
        pool=pool,
        settings=settings,
        embedder=embedder,
        skill_repo_factory=_skill_repo,
        category_repo_factory=_category_repo,
        registry_service_factory=_registry,
        discovery_service_factory=_discovery,
    )


async def close_container(container: ServiceContainer) -> None:
    """Release resources held by the container."""
    await container.pool.close()
