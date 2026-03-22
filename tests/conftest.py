"""Shared test fixtures."""

import json
import uuid
from collections.abc import AsyncIterator

import asyncpg
import pytest


async def _init_conn(conn: asyncpg.Connection) -> None:
    """Set up codecs for each connection."""
    await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")


@pytest.fixture(scope="session")
async def db_pool() -> AsyncIterator[asyncpg.Pool]:
    pool = await asyncpg.create_pool(
        "postgresql://loom:loom@localhost:5434/loom",
        min_size=1,
        max_size=5,
        init=_init_conn,
    )
    assert pool is not None
    yield pool
    await pool.close()


@pytest.fixture
async def db_conn(db_pool: asyncpg.Pool) -> AsyncIterator[asyncpg.Connection]:
    conn = await db_pool.acquire()
    tx = conn.transaction()
    await tx.start()
    try:
        yield conn
    finally:
        await tx.rollback()
        await db_pool.release(conn)


@pytest.fixture
async def test_author_id(db_conn: asyncpg.Connection) -> uuid.UUID:
    """Insert a test user and return the author_id."""
    author_id = uuid.uuid4()
    await db_conn.execute(
        "INSERT INTO users (id, handle, email, api_key, role) VALUES ($1, $2, $3, $4, $5)",
        author_id,
        "testuser",
        "test@example.com",
        "test-api-key",
        "contributor",
    )
    return author_id
