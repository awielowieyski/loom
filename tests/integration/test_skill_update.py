"""Integration tests for skill update (version bump)."""

import uuid

import asyncpg
import pytest

from loom.db.repositories.category_repo import CategoryRepo
from loom.db.repositories.skill_repo import SkillRepo
from loom.models.category import CategoryCreate
from loom.models.common import EvalScenario, EvalSpec
from loom.models.skill import SkillCreate, SkillUpdate
from loom.services.eval import EvalService
from loom.services.registry import RegistryService


@pytest.fixture
async def registry(db_conn: asyncpg.Connection) -> RegistryService:
    cat_repo = CategoryRepo(db_conn)
    skill_repo = SkillRepo(db_conn)
    eval_service = EvalService()
    return RegistryService(skill_repo=skill_repo, category_repo=cat_repo, eval_service=eval_service)


@pytest.fixture
async def setup(db_conn: asyncpg.Connection) -> uuid.UUID:
    """Create prerequisite category and user, return author_id."""
    await CategoryRepo(db_conn).create(CategoryCreate(slug="update-test-cat", name="Update Test"))
    author_id = await db_conn.fetchval(
        """
        INSERT INTO users (handle, email, api_key, role)
        VALUES ($1, $2, $3, 'contributor')
        RETURNING id
        """,
        f"user-{uuid.uuid4().hex[:8]}",
        f"user-{uuid.uuid4().hex[:8]}@example.com",
        f"key-{uuid.uuid4().hex}",
    )
    return author_id  # type: ignore[return-value]


async def test_update_skill_version_bump(registry: RegistryService, setup: uuid.UUID) -> None:
    """Create a skill at v1.0.0, update to v2.0.0, verify new version is current."""
    author_id = setup
    slug = f"update-skill-{uuid.uuid4().hex[:8]}"

    data = SkillCreate(
        slug=slug,
        name="Update Test Skill",
        description="A skill for update tests",
        content="This is valid content for the update skill that is long enough",
        category_slug="update-test-cat",
        version="1.0.0",
        eval_spec=EvalSpec(
            scenarios=[EvalScenario(description="d", input_context="c", success_criteria="s")]
        ),
    )
    created = await registry.create_skill(data, author_id=author_id)
    assert created.version == "1.0.0"

    update = SkillUpdate(
        version="2.0.0",
        description="Updated description for version 2",
        changelog="Improved description",
    )
    updated = await registry.update_skill(slug, update, author_id=author_id)

    assert updated.version == "2.0.0"
    assert updated.description == "Updated description for version 2"
    assert updated.slug == slug


async def test_update_skill_old_version_retrievable(
    registry: RegistryService, setup: uuid.UUID
) -> None:
    """Old version should still be retrievable after update."""
    author_id = setup
    slug = f"versioned-update-{uuid.uuid4().hex[:8]}"

    data = SkillCreate(
        slug=slug,
        name="Versioned Update Skill",
        description="A skill for version retrieval tests",
        content="This is valid content for the versioned update skill that is long enough",
        category_slug="update-test-cat",
        version="1.0.0",
        eval_spec=EvalSpec(
            scenarios=[EvalScenario(description="d", input_context="c", success_criteria="s")]
        ),
    )
    await registry.create_skill(data, author_id=author_id)

    update = SkillUpdate(
        version="1.1.0",
        content="Updated content for version 1.1.0 which is long enough to pass validation",
        changelog="Minor content update",
    )
    await registry.update_skill(slug, update, author_id=author_id)

    # Current version is the updated one
    current = await registry.get_skill(slug)
    assert current is not None
    assert current.version == "1.1.0"

    # Old version still retrievable
    old = await registry.get_skill(slug, version="1.0.0")
    assert old is not None
    assert old.version == "1.0.0"


async def test_update_skill_not_found(registry: RegistryService, setup: uuid.UUID) -> None:
    """Updating a non-existent slug should raise ValueError."""
    author_id = setup
    update = SkillUpdate(version="2.0.0")
    with pytest.raises(ValueError, match="not found"):
        await registry.update_skill("no-such-skill", update, author_id=author_id)
