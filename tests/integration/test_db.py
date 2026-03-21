import asyncpg
import pytest


@pytest.mark.asyncio
async def test_database_connection():
    """Verify we can connect to the test database."""
    conn = await asyncpg.connect(
        "postgresql://loom:loom@localhost:5434/loom"
    )
    try:
        result = await conn.fetchval("SELECT 1")
        assert result == 1
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_pgvector_extension():
    """Verify pgvector extension is available."""
    conn = await asyncpg.connect(
        "postgresql://loom:loom@localhost:5434/loom"
    )
    try:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        result = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
        )
        assert result is True
    finally:
        await conn.close()
