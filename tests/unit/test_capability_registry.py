"""Tests for CapabilityRegistryService."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from loom.models.capability import (
    Capability,
    CapabilityCreate,
    CapabilityStep,
    CapabilitySummary,
    CapabilityUpdate,
)
from loom.models.category import Category
from loom.models.common import (
    APIDependency,
    CostProfile,
    DependencyDeclaration,
    MCPServerDependency,
    TrustRequirements,
    TrustTier,
)
from loom.services.capability_registry import CapabilityRegistryService


def _make_step(slug: str, role: str = "test role", **kwargs: object) -> CapabilityStep:
    return CapabilityStep(skill_ref=f"loom://{slug}", role=role, **kwargs)


def _make_category(slug: str = "test-cat") -> Category:
    return Category(
        id=uuid.uuid4(),
        slug=slug,
        name="Test Category",
        description="A test category",
        parent_id=None,
        created_at=None,
    )


def _make_capability(
    slug: str = "test-cap",
    steps: list[CapabilityStep] | None = None,
    **kwargs: object,
) -> Capability:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "slug": slug,
        "name": slug,
        "description": f"Description for {slug}",
        "category_id": uuid.uuid4(),
        "tags": [],
        "scope": "community",
        "version": "1.0.0",
        "author_id": uuid.uuid4(),
        "trust_tier": TrustTier.COMMUNITY,
        "steps": steps or [_make_step("skill-a", "Step A")],
        "preconditions": [],
        "expected_outcome": "",
        "data_flow": [],
        "cost_profile": CostProfile.FREE,
        "cost_drivers": [],
        "estimated_duration": "slow",
    }
    defaults.update(kwargs)
    return Capability(**defaults)  # type: ignore[arg-type]


def _make_create(
    slug: str = "test-cap",
    steps: list[CapabilityStep] | None = None,
    **kwargs: object,
) -> CapabilityCreate:
    defaults: dict[str, object] = {
        "slug": slug,
        "name": slug,
        "description": f"Description for {slug}",
        "category_slug": "test-cat",
        "version": "1.0.0",
        "steps": steps or [_make_step("skill-a", "Step A")],
    }
    defaults.update(kwargs)
    return CapabilityCreate(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def mock_capability_repo() -> MagicMock:
    repo = MagicMock()
    repo.create = AsyncMock()
    repo.get_by_slug = AsyncMock(return_value=None)
    repo.update = AsyncMock()
    repo.list_all = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_category_repo() -> MagicMock:
    repo = MagicMock()
    repo.get_by_slug = AsyncMock(return_value=_make_category())
    return repo


@pytest.fixture
def mock_embedder() -> MagicMock:
    embedder = MagicMock()
    embed_result = MagicMock()
    embed_result.embeddings = [[0.1] * 1536]
    embedder.embed_query = AsyncMock(return_value=embed_result)
    return embedder


@pytest.fixture
def service(
    mock_capability_repo: MagicMock,
    mock_category_repo: MagicMock,
    mock_embedder: MagicMock,
) -> CapabilityRegistryService:
    return CapabilityRegistryService(
        capability_repo=mock_capability_repo,
        category_repo=mock_category_repo,
        embedder=mock_embedder,
    )


# ------------------------------------------------------------------
# Task 4: Basic CRUD
# ------------------------------------------------------------------


async def test_create_capability_with_valid_steps(
    service: CapabilityRegistryService,
    mock_capability_repo: MagicMock,
    mock_category_repo: MagicMock,
) -> None:
    expected = _make_capability()
    mock_capability_repo.create = AsyncMock(return_value=expected)

    data = _make_create()
    result = await service.create_capability(data, author_id=uuid.uuid4())

    assert result.slug == expected.slug
    mock_capability_repo.create.assert_awaited_once()
    mock_category_repo.get_by_slug.assert_awaited_once_with("test-cat")


async def test_create_capability_step_missing_uri_fails(
    service: CapabilityRegistryService,
) -> None:
    """Step with bare slug (no URI prefix) is rejected by the model validator."""
    with pytest.raises((ValueError, Exception), match="URI scheme prefix"):
        CapabilityCreate(
            slug="bad-cap",
            name="Bad",
            description="Bad cap",
            category_slug="test-cat",
            version="1.0.0",
            steps=[CapabilityStep(skill_ref="bare-slug", role="test")],
        )


async def test_create_with_nonexistent_category_fails(
    service: CapabilityRegistryService,
    mock_category_repo: MagicMock,
) -> None:
    mock_category_repo.get_by_slug = AsyncMock(return_value=None)
    data = _make_create(slug="orphan")

    with pytest.raises(ValueError, match="Category not found"):
        await service.create_capability(data, author_id=uuid.uuid4())


async def test_get_capability_by_slug(
    service: CapabilityRegistryService,
    mock_capability_repo: MagicMock,
) -> None:
    expected = _make_capability(slug="my-cap")
    mock_capability_repo.get_by_slug = AsyncMock(return_value=expected)

    result = await service.get_capability("my-cap")
    assert result is not None
    assert result.slug == "my-cap"


async def test_update_capability_creates_version(
    service: CapabilityRegistryService,
    mock_capability_repo: MagicMock,
) -> None:
    existing = _make_capability(slug="update-me")
    updated = _make_capability(slug="update-me", version="2.0.0")
    mock_capability_repo.get_by_slug = AsyncMock(return_value=existing)
    mock_capability_repo.update = AsyncMock(return_value=updated)

    data = CapabilityUpdate(version="2.0.0", description="Updated description")
    result = await service.update_capability("update-me", data, author_id=uuid.uuid4())

    assert result.slug == "update-me"
    mock_capability_repo.update.assert_awaited_once()


async def test_update_nonexistent_capability_fails(
    service: CapabilityRegistryService,
    mock_capability_repo: MagicMock,
) -> None:
    mock_capability_repo.get_by_slug = AsyncMock(return_value=None)

    data = CapabilityUpdate(version="2.0.0")
    with pytest.raises(ValueError, match="Capability not found"):
        await service.update_capability("no-such", data, author_id=uuid.uuid4())


async def test_list_capabilities(
    service: CapabilityRegistryService,
    mock_capability_repo: MagicMock,
) -> None:
    summaries = [
        CapabilitySummary(
            id=uuid.uuid4(),
            slug="cap-a",
            name="Cap A",
            description="A",
            category_id=uuid.uuid4(),
            tags=[],
            version="1.0.0",
            trust_tier=TrustTier.COMMUNITY,
            cost_profile=CostProfile.FREE,
            estimated_duration="slow",
            step_count=2,
        ),
    ]
    mock_capability_repo.list_all = AsyncMock(return_value=summaries)

    result = await service.list_capabilities()
    assert len(result) == 1
    assert result[0].slug == "cap-a"


# ------------------------------------------------------------------
# Task 6: Dependency Aggregation
# ------------------------------------------------------------------


def test_aggregate_dependencies_deduplicates_mcp_by_uri() -> None:
    steps = [_make_step("a"), _make_step("b")]
    deps = [
        DependencyDeclaration(
            mcp_servers=[MCPServerDependency(uri="mcp://server-a")],
        ),
        DependencyDeclaration(
            mcp_servers=[MCPServerDependency(uri="mcp://server-a")],
        ),
    ]

    result = CapabilityRegistryService.aggregate_dependencies(steps, deps)
    assert len(result.mcp_servers) == 1
    assert result.mcp_servers[0].uri == "mcp://server-a"


def test_aggregate_dependencies_unions_different_deps() -> None:
    steps = [_make_step("a"), _make_step("b")]
    deps = [
        DependencyDeclaration(
            mcp_servers=[MCPServerDependency(uri="mcp://server-a")],
            apis=[APIDependency(name="api-x")],
        ),
        DependencyDeclaration(
            mcp_servers=[MCPServerDependency(uri="mcp://server-b")],
            apis=[APIDependency(name="api-y")],
        ),
    ]

    result = CapabilityRegistryService.aggregate_dependencies(steps, deps)
    assert len(result.mcp_servers) == 2
    assert len(result.apis) == 2


def test_aggregate_dependencies_highest_classification() -> None:
    steps = [_make_step("a"), _make_step("b")]
    deps = [
        DependencyDeclaration(
            trust_requirements=TrustRequirements(data_classification="internal"),
        ),
        DependencyDeclaration(
            trust_requirements=TrustRequirements(data_classification="confidential"),
        ),
    ]

    result = CapabilityRegistryService.aggregate_dependencies(steps, deps)
    assert result.trust_requirements.data_classification == "confidential"


def test_aggregate_dependencies_network_access_any() -> None:
    steps = [_make_step("a"), _make_step("b")]
    deps = [
        DependencyDeclaration(
            trust_requirements=TrustRequirements(network_access=False),
        ),
        DependencyDeclaration(
            trust_requirements=TrustRequirements(network_access=True),
        ),
    ]

    result = CapabilityRegistryService.aggregate_dependencies(steps, deps)
    assert result.trust_requirements.network_access is True


def test_aggregate_dependencies_deduplicates_api_by_name() -> None:
    steps = [_make_step("a"), _make_step("b")]
    deps = [
        DependencyDeclaration(apis=[APIDependency(name="openai")]),
        DependencyDeclaration(apis=[APIDependency(name="openai")]),
    ]

    result = CapabilityRegistryService.aggregate_dependencies(steps, deps)
    assert len(result.apis) == 1
    assert result.apis[0].name == "openai"


def test_aggregate_dependencies_empty_deps() -> None:
    """Aggregating empty dependency lists returns an empty declaration."""
    steps = [_make_step("a")]
    deps: list[DependencyDeclaration] = [DependencyDeclaration()]

    result = CapabilityRegistryService.aggregate_dependencies(steps, deps)
    assert result.mcp_servers == []
    assert result.apis == []
    assert result.trust_requirements.data_classification == "none"
    assert result.trust_requirements.network_access is False


def test_aggregate_dependencies_no_network_when_none_needs_it() -> None:
    """network_access stays False when no step requires it."""
    steps = [_make_step("a"), _make_step("b")]
    deps = [
        DependencyDeclaration(
            trust_requirements=TrustRequirements(network_access=False),
        ),
        DependencyDeclaration(
            trust_requirements=TrustRequirements(network_access=False),
        ),
    ]

    result = CapabilityRegistryService.aggregate_dependencies(steps, deps)
    assert result.trust_requirements.network_access is False
