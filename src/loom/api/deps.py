"""FastAPI dependency injection wiring."""

from collections.abc import AsyncIterator
from typing import Annotated

import asyncpg
from fastapi import Depends, Request

from loom.db.repositories.behavioral_eval_repo import BehavioralEvalRepo
from loom.db.repositories.capability_repo import CapabilityRepo
from loom.db.repositories.category_repo import CategoryRepo
from loom.db.repositories.eval_repo import EvalRepo
from loom.db.repositories.skill_repo import SkillRepo
from loom.db.repositories.usage_repo import UsageRepo
from loom.services.activity_feed import ActivityFeedService
from loom.services.capability_discovery import CapabilityDiscoveryService
from loom.services.capability_registry import CapabilityRegistryService
from loom.services.container import ServiceContainer
from loom.services.discovery import DiscoveryService
from loom.services.governance_service import GovernanceService
from loom.services.registry import RegistryService
from loom.services.stats_service import StatsService
from loom.services.unified_resolver import UnifiedResolver


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


def get_capability_repo(
    conn: Annotated[asyncpg.Connection, Depends(get_conn)],
    container: Annotated[ServiceContainer, Depends(get_container)],
) -> CapabilityRepo:
    return container.capability_repo_factory(conn)


def get_capability_registry_service(
    capability_repo: Annotated[CapabilityRepo, Depends(get_capability_repo)],
    category_repo: Annotated[CategoryRepo, Depends(get_category_repo)],
    container: Annotated[ServiceContainer, Depends(get_container)],
) -> CapabilityRegistryService:
    return container.capability_registry_factory(capability_repo, category_repo)


def get_capability_discovery_service(
    capability_repo: Annotated[CapabilityRepo, Depends(get_capability_repo)],
    skill_repo: Annotated[SkillRepo, Depends(get_skill_repo)],
    container: Annotated[ServiceContainer, Depends(get_container)],
) -> CapabilityDiscoveryService:
    return container.capability_discovery_factory(capability_repo, skill_repo)


def get_unified_resolver(
    skill_repo: Annotated[SkillRepo, Depends(get_skill_repo)],
    capability_repo: Annotated[CapabilityRepo, Depends(get_capability_repo)],
    container: Annotated[ServiceContainer, Depends(get_container)],
) -> UnifiedResolver:
    return container.unified_resolver_factory(skill_repo, capability_repo)


def get_usage_repo(
    conn: Annotated[asyncpg.Connection, Depends(get_conn)],
    container: Annotated[ServiceContainer, Depends(get_container)],
) -> UsageRepo:
    return container.usage_repo_factory(conn)


def get_behavioral_eval_repo(
    conn: Annotated[asyncpg.Connection, Depends(get_conn)],
    container: Annotated[ServiceContainer, Depends(get_container)],
) -> BehavioralEvalRepo:
    return container.behavioral_eval_repo_factory(conn)


def get_activity_feed_service(
    conn: Annotated[asyncpg.Connection, Depends(get_conn)],
    container: Annotated[ServiceContainer, Depends(get_container)],
) -> ActivityFeedService:
    return container.activity_feed_factory(conn)


def get_stats_service(
    conn: Annotated[asyncpg.Connection, Depends(get_conn)],
    container: Annotated[ServiceContainer, Depends(get_container)],
) -> StatsService:
    return container.stats_service_factory(conn)


def get_governance_service(
    conn: Annotated[asyncpg.Connection, Depends(get_conn)],
    container: Annotated[ServiceContainer, Depends(get_container)],
) -> GovernanceService:
    return container.governance_service_factory(conn)
