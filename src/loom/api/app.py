"""FastAPI application factory."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from loom.services.container import close_container, create_container
from loom.settings import LoomSettings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create shared resources on startup; clean up on shutdown."""
    settings = LoomSettings()
    container = await create_container(settings)
    app.state.container = container

    # Create arq Redis pool for job enqueueing (eval trigger, etc.)
    arq_pool = None
    try:
        from arq import create_pool as create_arq_pool

        from loom.worker import _redis_settings_from_url

        arq_pool = await create_arq_pool(_redis_settings_from_url(settings.redis.url))
    except Exception:
        logger.warning("Redis unavailable — background job enqueueing disabled", exc_info=True)
    app.state.arq_pool = arq_pool

    try:
        yield
    finally:
        if arq_pool is not None:
            await arq_pool.close()
        await close_container(container)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Loom", version="0.1.0", lifespan=lifespan)

    from loom.api.routes.activity import router as activity_router
    from loom.api.routes.artifacts import router as artifacts_router
    from loom.api.routes.capabilities import router as capabilities_router
    from loom.api.routes.categories import router as categories_router
    from loom.api.routes.embeddings import router as embeddings_router
    from loom.api.routes.eval import router as eval_router
    from loom.api.routes.governance import router as governance_router
    from loom.api.routes.health import router as health_router
    from loom.api.routes.resolve import router as resolve_router
    from loom.api.routes.skills import router as skills_router
    from loom.api.routes.skills_m4 import router as skills_m4_router
    from loom.api.routes.stats import router as stats_router
    from loom.api.routes.timeline import router as timeline_router
    from loom.api.routes.usage import router as usage_router

    app.include_router(health_router)
    app.include_router(categories_router)
    app.include_router(skills_router)
    app.include_router(eval_router)
    app.include_router(capabilities_router)
    app.include_router(usage_router)
    app.include_router(skills_m4_router)
    app.include_router(resolve_router)
    app.include_router(activity_router)
    app.include_router(artifacts_router)
    app.include_router(embeddings_router)
    app.include_router(stats_router)
    app.include_router(governance_router)
    app.include_router(timeline_router)

    return app
