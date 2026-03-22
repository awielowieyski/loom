"""Integration tests for the health endpoint."""

import httpx
import pytest

from loom.api.app import create_app


@pytest.fixture
def app():
    return create_app()


async def test_health_returns_ok(app) -> None:
    """GET /health should return 200 with {"status": "ok"}."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
