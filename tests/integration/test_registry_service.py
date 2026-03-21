"""Integration tests for RegistryService."""

import uuid

import asyncpg
import pytest

from loom.db.repositories.category_repo import CategoryRepo
from loom.db.repositories.skill_repo import SkillRepo
from loom.models.category import CategoryCreate
from loom.models.common import EvalScenario, EvalSpec
from loom.models.skill import SkillCreate
from loom.services.eval import EvalService
from loom.services.registry import RegistryService


@pytest.fixture
async def registry(db_conn: asyncpg.Connection) -> RegistryService:
    cat_repo = CategoryRepo(db_conn)
    skill_repo = SkillRepo(db_conn)
    eval_service = EvalService()
    return RegistryService(skill_repo=skill_repo, category_repo=cat_repo, eval_service=eval_service)


@pytest.fixture
async def setup(db_conn: asyncpg.Connection, registry: RegistryService) -> uuid.UUID:
    """Create prerequisite category and user, return author_id."""
    await CategoryRepo(db_conn).create(CategoryCreate(slug="code-gen", name="Code Generation"))
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


async def _make_skill(**overrides: object) -> SkillCreate:
    defaults: dict[str, object] = {
        "slug": f"reg-skill-{uuid.uuid4().hex[:8]}",
        "name": "Registry Skill",
        "description": "A skill for registry tests",
        "content": "This is valid content for the registry skill that is long enough",
        "category_slug": "code-gen",
        "version": "1.0.0",
        "eval_spec": EvalSpec(
            scenarios=[EvalScenario(description="d", input_context="c", success_criteria="s")]
        ),
    }
    defaults.update(overrides)
    return SkillCreate(**defaults)  # type: ignore[arg-type]


async def test_create_skill_succeeds(registry: RegistryService, setup: uuid.UUID) -> None:
    author_id = setup
    data = await _make_skill()
    skill = await registry.create_skill(data, author_id=author_id)
    assert skill.id is not None
    assert skill.slug == data.slug
    assert skill.version == "1.0.0"


async def test_create_skill_fails_validation(registry: RegistryService, setup: uuid.UUID) -> None:
    author_id = setup
    data = await _make_skill(content="short")
    with pytest.raises(ValueError, match="content"):
        await registry.create_skill(data, author_id=author_id)


async def test_create_skill_fails_unknown_category(
    registry: RegistryService, setup: uuid.UUID
) -> None:
    author_id = setup
    data = await _make_skill(category_slug="no-such-category")
    with pytest.raises(ValueError, match="[Cc]ategory"):
        await registry.create_skill(data, author_id=author_id)


async def test_get_skill(registry: RegistryService, setup: uuid.UUID) -> None:
    author_id = setup
    data = await _make_skill()
    created = await registry.create_skill(data, author_id=author_id)

    fetched = await registry.get_skill(data.slug)
    assert fetched is not None
    assert fetched.id == created.id


async def test_list_skills(registry: RegistryService, setup: uuid.UUID) -> None:
    author_id = setup
    data = await _make_skill()
    await registry.create_skill(data, author_id=author_id)

    skills = await registry.list_skills()
    assert any(s.slug == data.slug for s in skills)
