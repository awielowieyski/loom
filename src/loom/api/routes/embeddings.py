"""Embedding map API routes."""

from typing import Annotated, Any

import asyncpg
from fastapi import APIRouter, Depends

from loom.api.deps import get_conn
from loom.api.middleware import verify_api_key
from loom.services.embedding_map import EmbeddingMapService

router = APIRouter(prefix="/api/v1/embeddings", tags=["embeddings"])

# Module-level singleton so the cache persists across requests
_embedding_map_service = EmbeddingMapService()


@router.get("/map")
async def get_embedding_map(
    _: Annotated[str | None, Depends(verify_api_key)],
    conn: Annotated[asyncpg.Connection, Depends(get_conn)],
) -> dict[str, list[dict[str, Any]]]:
    """Return a 2D embedding map of all skills and capabilities."""
    return await _embedding_map_service.compute_map(conn)
