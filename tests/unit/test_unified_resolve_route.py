"""Tests for the unified /api/v1/resolve route."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from loom.models.common import CostProfile, TrustTier
from loom.models.resolution import (
    ResolutionError,
    ResolvedResult,
    ResolvedSkill,
)
from loom.models.skill import Skill


def _make_skill(slug: str = "test-skill") -> Skill:
    return Skill(
        id=uuid.uuid4(),
        slug=slug,
        name=slug,
        description=f"Description for {slug}",
        content=f"Content for {slug}",
        category_id=uuid.uuid4(),
        tags=[],
        scope="community",
        version="1.0.0",
        author_id=uuid.uuid4(),
        trust_tier=TrustTier.COMMUNITY,
        cost_profile=CostProfile.FREE,
        cost_drivers=[],
        estimated_duration="fast",
    )


def _make_resolved_result(slug: str = "test-skill") -> ResolvedResult:
    return ResolvedResult(
        type="skill",
        skill=ResolvedSkill(
            skill=_make_skill(slug),
            selection_rationale=[f"Selected {slug!r} as best match"],
        ),
    )


@pytest.fixture
def mock_resolver() -> MagicMock:
    resolver = MagicMock()
    resolver.resolve = AsyncMock(return_value=_make_resolved_result())
    return resolver


@pytest.fixture
def client(mock_resolver: MagicMock) -> TestClient:
    """Create a test client with mocked dependencies."""
    from loom.api.app import create_app

    app = create_app()

    # Override the dependency
    from loom.api.deps import get_unified_resolver
    from loom.api.middleware import verify_api_key

    app.dependency_overrides[verify_api_key] = lambda: "test-key"
    app.dependency_overrides[get_unified_resolver] = lambda: mock_resolver

    return TestClient(app, raise_server_exceptions=False)


def test_resolve_returns_skill_result(client: TestClient, mock_resolver: MagicMock) -> None:
    """POST /api/v1/resolve returns ResolvedResult on success."""
    response = client.post(
        "/api/v1/resolve",
        json={"task_description": "deploy to production"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "skill"
    assert data["skill"]["skill"]["slug"] == "test-skill"
    mock_resolver.resolve.assert_called_once()


def test_resolve_returns_404_on_resolution_error(
    client: TestClient, mock_resolver: MagicMock
) -> None:
    """POST /api/v1/resolve returns 404 when resolution fails."""
    mock_resolver.resolve = AsyncMock(
        return_value=ResolutionError(
            error="no_match",
            message="No skills found",
        )
    )
    response = client.post(
        "/api/v1/resolve",
        json={"task_description": "nonexistent task"},
    )
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["error"] == "no_match"


def test_resolve_passes_type_filter(client: TestClient, mock_resolver: MagicMock) -> None:
    """POST /api/v1/resolve passes type filter to resolver."""
    client.post(
        "/api/v1/resolve",
        json={"task_description": "do something", "type": "capability"},
    )
    call_kwargs = mock_resolver.resolve.call_args
    assert call_kwargs.kwargs["type_filter"] == "capability"


def test_resolve_passes_context(client: TestClient, mock_resolver: MagicMock) -> None:
    """POST /api/v1/resolve passes context to resolver."""
    client.post(
        "/api/v1/resolve",
        json={
            "task_description": "do something",
            "context": {"trust_floor": "verified"},
        },
    )
    call_kwargs = mock_resolver.resolve.call_args
    assert call_kwargs.kwargs["context"] is not None
    assert call_kwargs.kwargs["context"].trust_floor == TrustTier.VERIFIED


def test_resolve_defaults_type_to_any(client: TestClient, mock_resolver: MagicMock) -> None:
    """POST /api/v1/resolve defaults type to 'any'."""
    client.post(
        "/api/v1/resolve",
        json={"task_description": "do something"},
    )
    call_kwargs = mock_resolver.resolve.call_args
    assert call_kwargs.kwargs["type_filter"] == "any"


def test_resolve_requires_api_key() -> None:
    """POST /api/v1/resolve requires an API key."""
    from loom.api.app import create_app

    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(
        "/api/v1/resolve",
        json={"task_description": "do something"},
    )
    assert response.status_code == 401
