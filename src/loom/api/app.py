"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from loom.services.container import close_container, create_container
from loom.settings import LoomSettings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create shared resources on startup; clean up on shutdown."""
    settings = LoomSettings()
    container = await create_container(settings)
    app.state.container = container
    try:
        yield
    finally:
        await close_container(container)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Loom", version="0.1.0", lifespan=lifespan)

    from loom.api.routes.categories import router as categories_router
    from loom.api.routes.eval import router as eval_router
    from loom.api.routes.health import router as health_router
    from loom.api.routes.skills import router as skills_router

    app.include_router(health_router)
    app.include_router(categories_router)
    app.include_router(skills_router)
    app.include_router(eval_router)

    return app
