"""Shared test fixtures."""

import os
import uuid
from collections.abc import AsyncIterator

import asyncpg
import pytest

from loom.db.engine import _init_connection

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://loom:loom@localhost:5434/loom",
)


@pytest.fixture(scope="session")
async def db_pool() -> AsyncIterator[asyncpg.Pool]:
    pool = await asyncpg.create_pool(
        TEST_DATABASE_URL,
        min_size=1,
        max_size=5,
        init=_init_connection,
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
