"""Shared service container — single place to wire up DB pool, embedder, and repo factories."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from cachetools import TTLCache

from loom.db.repositories.behavioral_eval_repo import BehavioralEvalRepo
from loom.db.repositories.capability_repo import CapabilityRepo
from loom.db.repositories.category_repo import CategoryRepo
from loom.db.repositories.eval_repo import EvalRepo
from loom.db.repositories.skill_repo import SkillRepo
from loom.db.repositories.usage_repo import UsageRepo
from loom.services.capability_discovery import CapabilityDiscoveryService
from loom.services.capability_registry import CapabilityRegistryService
from loom.services.discovery import DiscoveryService
from loom.services.eval import EvalService
from loom.services.prompt_registry import PromptRegistry
from loom.services.registry import RegistryService
from loom.services.score_aggregator import ScoreAggregator  # noqa: TC001
from loom.services.static_analyser import StaticAnalyser  # noqa: TC001
from loom.services.unified_resolver import UnifiedResolver
from loom.services.usage_service import UsageService

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

    # M2: eval pipeline components
    prompt_registry: PromptRegistry
    eval_repo_factory: Callable[[asyncpg.Connection], EvalRepo]
    static_analyser: StaticAnalyser
    score_aggregator: ScoreAggregator

    # M3: capability composition
    capability_repo_factory: Callable[[asyncpg.Connection], CapabilityRepo]
    capability_registry_factory: Callable[[CapabilityRepo, CategoryRepo], CapabilityRegistryService]
    capability_discovery_factory: Callable[[CapabilityRepo, SkillRepo], CapabilityDiscoveryService]
    unified_resolver_factory: Callable[[SkillRepo, CapabilityRepo], UnifiedResolver]

    # M4: living registry
    usage_repo_factory: Callable[[asyncpg.Connection], UsageRepo]
    behavioral_eval_repo_factory: Callable[[asyncpg.Connection], BehavioralEvalRepo]
    usage_service_factory: Callable[[UsageRepo, SkillRepo], UsageService]


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

    prompt_registry = PromptRegistry()

    pipeline_cfg = settings.pipeline
    static_analyser = StaticAnalyser(
        max_content_length=pipeline_cfg.max_content_length,
        max_steps=pipeline_cfg.max_steps,
        max_dependencies=pipeline_cfg.max_dependencies,
    )
    score_aggregator = ScoreAggregator(pass_threshold=pipeline_cfg.pass_threshold)

    def _skill_repo(conn: asyncpg.Connection) -> SkillRepo:
        return SkillRepo(conn)

    def _category_repo(conn: asyncpg.Connection) -> CategoryRepo:
        return CategoryRepo(conn)

    def _eval_repo(conn: asyncpg.Connection) -> EvalRepo:
        return EvalRepo(conn)

    def _registry(skill_repo: SkillRepo, category_repo: CategoryRepo) -> RegistryService:
        return RegistryService(
            skill_repo=skill_repo,
            category_repo=category_repo,
            eval_service=eval_service,
        )

    def _discovery(skill_repo: SkillRepo) -> DiscoveryService:
        return DiscoveryService(skill_repo=skill_repo, embedder=embedder, embed_cache=embed_cache)

    def _capability_repo(conn: asyncpg.Connection) -> CapabilityRepo:
        return CapabilityRepo(conn)

    def _capability_registry(
        cap_repo: CapabilityRepo, cat_repo: CategoryRepo
    ) -> CapabilityRegistryService:
        return CapabilityRegistryService(
            capability_repo=cap_repo,
            category_repo=cat_repo,
            embedder=embedder,
        )

    def _capability_discovery(
        cap_repo: CapabilityRepo, skill_repo: SkillRepo
    ) -> CapabilityDiscoveryService:
        return CapabilityDiscoveryService(
            capability_repo=cap_repo,
            skill_repo=skill_repo,
            embedder=embedder,
            embed_cache=embed_cache,
        )

    def _usage_repo(conn: asyncpg.Connection) -> UsageRepo:
        return UsageRepo(conn)

    def _behavioral_eval_repo(conn: asyncpg.Connection) -> BehavioralEvalRepo:
        return BehavioralEvalRepo(conn)

    def _usage_service(usage_repo: UsageRepo, skill_repo: SkillRepo) -> UsageService:
        return UsageService(usage_repo=usage_repo, skill_repo=skill_repo)

    def _unified_resolver(skill_repo: SkillRepo, cap_repo: CapabilityRepo) -> UnifiedResolver:
        return UnifiedResolver(
            discovery_service=_discovery(skill_repo),
            capability_discovery_service=_capability_discovery(cap_repo, skill_repo),
        )

    return ServiceContainer(
        pool=pool,
        settings=settings,
        embedder=embedder,
        skill_repo_factory=_skill_repo,
        category_repo_factory=_category_repo,
        registry_service_factory=_registry,
        discovery_service_factory=_discovery,
        prompt_registry=prompt_registry,
        eval_repo_factory=_eval_repo,
        static_analyser=static_analyser,
        score_aggregator=score_aggregator,
        capability_repo_factory=_capability_repo,
        capability_registry_factory=_capability_registry,
        capability_discovery_factory=_capability_discovery,
        unified_resolver_factory=_unified_resolver,
        usage_repo_factory=_usage_repo,
        behavioral_eval_repo_factory=_behavioral_eval_repo,
        usage_service_factory=_usage_service,
    )


async def close_container(container: ServiceContainer) -> None:
    """Release resources held by the container."""
    await container.pool.close()
