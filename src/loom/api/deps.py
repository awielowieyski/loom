"""FastAPI dependency injection wiring."""

from collections.abc import AsyncIterator
from typing import Annotated

import asyncpg
from fastapi import Depends, Request

from loom.db.repositories.category_repo import CategoryRepo
from loom.db.repositories.skill_repo import SkillRepo
from loom.services.discovery import DiscoveryService
from loom.services.eval import EvalService
from loom.services.registry import RegistryService


def get_pool(request: Request) -> asyncpg.Pool:
    """Return the connection pool from app state."""
    pool: asyncpg.Pool = request.app.state.pool
    return pool


async def get_conn(
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
) -> AsyncIterator[asyncpg.Connection]:
    """Acquire a connection from the pool, yield it, then release."""
    async with pool.acquire() as conn:
        yield conn


def get_skill_repo(
    conn: Annotated[asyncpg.Connection, Depends(get_conn)],
) -> SkillRepo:
    return SkillRepo(conn)


def get_category_repo(
    conn: Annotated[asyncpg.Connection, Depends(get_conn)],
) -> CategoryRepo:
    return CategoryRepo(conn)


def get_eval_service() -> EvalService:
    return EvalService()


def get_registry_service(
    skill_repo: Annotated[SkillRepo, Depends(get_skill_repo)],
    category_repo: Annotated[CategoryRepo, Depends(get_category_repo)],
    eval_service: Annotated[EvalService, Depends(get_eval_service)],
) -> RegistryService:
    return RegistryService(
        skill_repo=skill_repo,
        category_repo=category_repo,
        eval_service=eval_service,
    )


def get_discovery_service(
    request: Request,
    skill_repo: Annotated[SkillRepo, Depends(get_skill_repo)],
) -> DiscoveryService:
    return DiscoveryService(skill_repo=skill_repo, embedder=request.app.state.embedder)
