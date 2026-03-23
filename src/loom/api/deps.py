"""FastAPI dependency injection wiring."""

from collections.abc import AsyncIterator
from typing import Annotated

import asyncpg
from fastapi import Depends, Request

from loom.db.repositories.category_repo import CategoryRepo
from loom.db.repositories.eval_repo import EvalRepo
from loom.db.repositories.skill_repo import SkillRepo
from loom.services.container import ServiceContainer
from loom.services.discovery import DiscoveryService
from loom.services.registry import RegistryService


def get_container(request: Request) -> ServiceContainer:
    """Return the service container from app state."""
    return request.app.state.container  # type: ignore[no-any-return]


async def get_conn(
    container: Annotated[ServiceContainer, Depends(get_container)],
) -> AsyncIterator[asyncpg.Connection]:
    """Acquire a connection from the pool, yield it, then release."""
    async with container.pool.acquire() as conn:
        yield conn


def get_skill_repo(
    conn: Annotated[asyncpg.Connection, Depends(get_conn)],
    container: Annotated[ServiceContainer, Depends(get_container)],
) -> SkillRepo:
    return container.skill_repo_factory(conn)


def get_category_repo(
    conn: Annotated[asyncpg.Connection, Depends(get_conn)],
    container: Annotated[ServiceContainer, Depends(get_container)],
) -> CategoryRepo:
    return container.category_repo_factory(conn)


def get_eval_repo(
    conn: Annotated[asyncpg.Connection, Depends(get_conn)],
    container: Annotated[ServiceContainer, Depends(get_container)],
) -> EvalRepo:
    return container.eval_repo_factory(conn)


def get_registry_service(
    skill_repo: Annotated[SkillRepo, Depends(get_skill_repo)],
    category_repo: Annotated[CategoryRepo, Depends(get_category_repo)],
    container: Annotated[ServiceContainer, Depends(get_container)],
) -> RegistryService:
    return container.registry_service_factory(skill_repo, category_repo)


def get_discovery_service(
    skill_repo: Annotated[SkillRepo, Depends(get_skill_repo)],
    container: Annotated[ServiceContainer, Depends(get_container)],
) -> DiscoveryService:
    return container.discovery_service_factory(skill_repo)
