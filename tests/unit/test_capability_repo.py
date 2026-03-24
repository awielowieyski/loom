"""Integration tests for CapabilityRepo."""

import uuid

import asyncpg
import pytest

from loom.db.repositories.capability_repo import CapabilityRepo
from loom.db.repositories.category_repo import CategoryRepo
from loom.models.capability import CapabilityStep, CapabilitySummary, DataFlowEdge
from loom.models.category import CategoryCreate
from loom.models.common import TrustTier


def _make_steps() -> list[CapabilityStep]:
    return [
        CapabilityStep(
            skill_ref="loom://review-pull-request",
            role="Structural code review",
            inputs={"diff": "$input.diff"},
            outputs={"review": "$result"},
        ),
        CapabilityStep(
            skill_ref="loom://review-security",
            role="Security analysis",
            inputs={"diff": "$input.diff"},
            outputs={"security": "$result"},
        ),
    ]


def _make_data_flow() -> list[DataFlowEdge]:
    return [
        DataFlowEdge(
            from_step="review-pull-request",
            to_step="review-security",
            classification="internal",
        )
    ]


@pytest.fixture
async def cap_repo_ctx(
    db_conn: asyncpg.Connection, test_author_id: uuid.UUID
) -> tuple[CapabilityRepo, uuid.UUID, uuid.UUID]:
    """Return (capability_repo, category_id, author_id)."""
    cat_repo = CategoryRepo(db_conn)
    cat = await cat_repo.create(
        CategoryCreate(slug=f"cap-cat-{uuid.uuid4().hex[:8]}", name="Cap Cat")
    )
    return CapabilityRepo(db_conn), cat.id, test_author_id


async def test_create_and_get_by_id(
    cap_repo_ctx: tuple[CapabilityRepo, uuid.UUID, uuid.UUID],
) -> None:
    repo, cat_id, author_id = cap_repo_ctx
    cap = await repo.create(
        slug="test-cap",
        name="Test Capability",
        description="A test capability",
        category_id=cat_id,
        tags=["test"],
        version="1.0.0",
        author_id=author_id,
        steps=_make_steps(),
        preconditions=["PR diff available"],
        expected_outcome="Combined review",
        data_flow=_make_data_flow(),
    )
    assert cap.id is not None
    assert cap.slug == "test-cap"
    assert cap.name == "Test Capability"
    assert len(cap.steps) == 2
    assert cap.steps[0].skill_ref == "loom://review-pull-request"
    assert cap.preconditions == ["PR diff available"]
    assert cap.expected_outcome == "Combined review"
    assert len(cap.data_flow) == 1
    assert cap.data_flow[0].classification == "internal"

    fetched = await repo.get_by_id(cap.id)
    assert fetched is not None
    assert fetched.id == cap.id
    assert len(fetched.steps) == 2


async def test_get_by_slug(
    cap_repo_ctx: tuple[CapabilityRepo, uuid.UUID, uuid.UUID],
) -> None:
    repo, cat_id, author_id = cap_repo_ctx
    await repo.create(
        slug="slug-cap",
        name="Slug Capability",
        description="A slug-lookup capability",
        category_id=cat_id,
        tags=[],
        version="1.0.0",
        author_id=author_id,
        steps=_make_steps(),
    )
    fetched = await repo.get_by_slug("slug-cap")
    assert fetched is not None
    assert fetched.slug == "slug-cap"


async def test_get_by_slug_missing(
    cap_repo_ctx: tuple[CapabilityRepo, uuid.UUID, uuid.UUID],
) -> None:
    repo, _, _ = cap_repo_ctx
    assert await repo.get_by_slug("nonexistent") is None


async def test_update_creates_version(
    cap_repo_ctx: tuple[CapabilityRepo, uuid.UUID, uuid.UUID],
) -> None:
    repo, cat_id, author_id = cap_repo_ctx
    cap = await repo.create(
        slug="update-cap",
        name="Update Capability",
        description="Original description",
        category_id=cat_id,
        tags=["v1"],
        version="1.0.0",
        author_id=author_id,
        steps=_make_steps(),
    )

    new_steps = _make_steps() + [
        CapabilityStep(
            skill_ref="loom://review-performance",
            role="Performance review",
        )
    ]
    updated = await repo.update(
        cap.id,
        version="2.0.0",
        author_id=author_id,
        steps=new_steps,
        description="Updated description",
        changelog="Added performance review step",
    )
    assert updated is not None
    assert updated.version == "2.0.0"
    assert updated.description == "Updated description"
    assert len(updated.steps) == 3

    versions = await repo.get_versions(cap.id)
    assert len(versions) == 2
    assert versions[0].version == "1.0.0"
    assert versions[1].version == "2.0.0"
    assert versions[1].changelog == "Added performance review step"


async def test_list_with_trust_tier_filter(
    cap_repo_ctx: tuple[CapabilityRepo, uuid.UUID, uuid.UUID],
) -> None:
    repo, cat_id, author_id = cap_repo_ctx
    await repo.create(
        slug="community-cap",
        name="Community Capability",
        description="A community capability",
        category_id=cat_id,
        tags=[],
        version="1.0.0",
        author_id=author_id,
        steps=_make_steps(),
        trust_tier=TrustTier.COMMUNITY,
    )
    await repo.create(
        slug="experimental-cap",
        name="Experimental Capability",
        description="An experimental capability",
        category_id=cat_id,
        tags=[],
        version="1.0.0",
        author_id=author_id,
        steps=_make_steps(),
        trust_tier=TrustTier.EXPERIMENTAL,
    )

    all_caps = await repo.list_all()
    slugs = [c.slug for c in all_caps]
    assert "community-cap" in slugs
    assert "experimental-cap" in slugs
    assert all(isinstance(c, CapabilitySummary) for c in all_caps)

    community = await repo.list_all(trust_tier=TrustTier.COMMUNITY)
    community_slugs = [c.slug for c in community]
    assert "community-cap" in community_slugs
    assert "experimental-cap" not in community_slugs


async def test_list_summary_has_step_count(
    cap_repo_ctx: tuple[CapabilityRepo, uuid.UUID, uuid.UUID],
) -> None:
    repo, cat_id, author_id = cap_repo_ctx
    await repo.create(
        slug="step-count-cap",
        name="Step Count Cap",
        description="Testing step_count",
        category_id=cat_id,
        tags=[],
        version="1.0.0",
        author_id=author_id,
        steps=_make_steps(),
    )
    caps = await repo.list_all()
    match = [c for c in caps if c.slug == "step-count-cap"]
    assert len(match) == 1
    assert match[0].step_count == 2


async def test_vector_search(
    cap_repo_ctx: tuple[CapabilityRepo, uuid.UUID, uuid.UUID],
) -> None:
    repo, cat_id, author_id = cap_repo_ctx
    embedding = [0.1] * 1536
    await repo.create(
        slug="embedded-cap",
        name="Embedded Capability",
        description="A capability with an embedding",
        category_id=cat_id,
        tags=[],
        version="1.0.0",
        author_id=author_id,
        steps=_make_steps(),
        embedding=embedding,
    )

    results = await repo.vector_search_summary(embedding, limit=10)
    assert len(results) >= 1
    assert any(c.slug == "embedded-cap" for c in results)
    assert all(isinstance(c, CapabilitySummary) for c in results)


async def test_get_version(
    cap_repo_ctx: tuple[CapabilityRepo, uuid.UUID, uuid.UUID],
) -> None:
    repo, cat_id, author_id = cap_repo_ctx
    cap = await repo.create(
        slug="version-cap",
        name="Version Cap",
        description="Version test",
        category_id=cat_id,
        tags=[],
        version="1.0.0",
        author_id=author_id,
        steps=_make_steps(),
    )

    v = await repo.get_version(cap.id, "1.0.0")
    assert v is not None
    assert v.version == "1.0.0"
    assert len(v.steps) == 2
    assert v.capability_id == cap.id

    missing = await repo.get_version(cap.id, "99.0.0")
    assert missing is None
