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


@pytest.fixture
async def test_category_id(db_conn: asyncpg.Connection) -> uuid.UUID:
    """Insert a test category and return the category_id."""
    category_id = uuid.uuid4()
    await db_conn.execute(
        "INSERT INTO categories (id, slug, name) VALUES ($1, $2, $3)",
        category_id,
        "test-category",
        "Test Category",
    )
    return category_id


@pytest.fixture
async def test_skill_id(
    db_conn: asyncpg.Connection,
    test_author_id: uuid.UUID,
    test_category_id: uuid.UUID,
) -> uuid.UUID:
    """Insert a test skill and return the skill_id."""
    skill_id = uuid.uuid4()
    await db_conn.execute(
        """
        INSERT INTO skills (
            id, slug, name, description, content, category_id, tags,
            scope, version, author_id, trust_tier, cost_profile,
            cost_drivers, estimated_duration, dependencies, eval_spec
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7,
            $8, $9, $10, $11, $12,
            $13, $14, $15, $16
        )
        """,
        skill_id,
        "test-skill",
        "Test Skill",
        "A test skill",
        "# Test\nDo the thing.",
        test_category_id,
        [],
        "community",
        "1.0.0",
        test_author_id,
        "experimental",
        "free",
        [],
        "fast",
        {},
        {},
    )
    return skill_id
