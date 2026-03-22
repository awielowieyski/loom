"""Database connection pool management."""

import asyncpg
from pgvector.asyncpg import register_vector


async def create_pool(database_url: str) -> asyncpg.Pool:
    """Create an asyncpg connection pool with pgvector support."""
    url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    pool = await asyncpg.create_pool(url, min_size=2, max_size=10, init=register_vector)
    if pool is None:
        raise RuntimeError("Failed to create asyncpg connection pool")
    return pool
