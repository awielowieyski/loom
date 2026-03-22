"""Database connection pool management."""

import json

import asyncpg
from pgvector.asyncpg import register_vector


async def _init_connection(conn: asyncpg.Connection) -> None:
    """Register codecs for pgvector and JSONB on each new connection."""
    await register_vector(conn)
    await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")


async def create_pool(database_url: str) -> asyncpg.Pool:
    """Create an asyncpg connection pool with pgvector and JSONB support."""
    url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    pool = await asyncpg.create_pool(url, min_size=2, max_size=10, init=_init_connection)
    if pool is None:
        raise RuntimeError("Failed to create asyncpg connection pool")
    return pool
