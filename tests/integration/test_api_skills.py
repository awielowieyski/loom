"""Integration tests for skill and category API routes."""

import pytest
from fastapi.testclient import TestClient

from loom.api.app import create_app

API_KEY = "test-key"
HEADERS = {"X-API-Key": API_KEY}


@pytest.fixture
def client():
    """TestClient triggers the lifespan, establishing DB + embedder state."""
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_list_categories_returns_200(client: TestClient) -> None:
    """GET /api/v1/categories should return 200 with a list."""
    response = client.get("/api/v1/categories", headers=HEADERS)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_categories_allows_anonymous_read(client: TestClient) -> None:
    """GET /api/v1/categories should allow anonymous reads."""
    response = client.get("/api/v1/categories")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_skills_returns_200(client: TestClient) -> None:
    """GET /api/v1/skills should return 200 with a list."""
    response = client.get("/api/v1/skills", headers=HEADERS)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_skills_allows_anonymous_read(client: TestClient) -> None:
    """GET /api/v1/skills should allow anonymous reads."""
    response = client.get("/api/v1/skills")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_skill_not_found(client: TestClient) -> None:
    """GET /api/v1/skills/{slug} should return 404 for unknown slug."""
    response = client.get("/api/v1/skills/no-such-skill", headers=HEADERS)
    assert response.status_code == 404
