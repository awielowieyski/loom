"""Integration tests for SkillRepo."""

import uuid

import asyncpg
import pytest

from loom.db.repositories.category_repo import CategoryRepo
from loom.db.repositories.skill_repo import SkillRepo
from loom.models.category import CategoryCreate
from loom.models.common import CostProfile, DependencyDeclaration, EvalScenario, EvalSpec, TrustTier
from loom.models.skill import SkillSummary


@pytest.fixture
async def repo_pair(db_conn: asyncpg.Connection) -> tuple[SkillRepo, uuid.UUID, uuid.UUID]:
    """Return (skill_repo, category_id, author_id) for a test transaction."""
    cat_repo = CategoryRepo(db_conn)
    cat = await cat_repo.create(CategoryCreate(slug=f"cat-{uuid.uuid4().hex[:8]}", name="Test Cat"))

    # Create a user for author_id
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

    return SkillRepo(db_conn), cat.id, author_id


async def test_create_and_get_by_id(repo_pair: tuple[SkillRepo, uuid.UUID, uuid.UUID]) -> None:
    repo, cat_id, author_id = repo_pair
    eval_spec = EvalSpec(
        scenarios=[EvalScenario(description="d", input_context="c", success_criteria="s")]
    )
    skill = await repo.create(
        slug="test-skill",
        name="Test Skill",
        description="A test skill",
        content="This is some content for the skill",
        category_id=cat_id,
        tags=["test"],
        version="1.0.0",
        author_id=author_id,
        dependencies=DependencyDeclaration(),
        eval_spec=eval_spec,
    )
    assert skill.id is not None
    assert skill.slug == "test-skill"
    assert skill.name == "Test Skill"

    fetched = await repo.get_by_id(skill.id)
    assert fetched is not None
    assert fetched.id == skill.id


async def test_get_by_slug_with_version(repo_pair: tuple[SkillRepo, uuid.UUID, uuid.UUID]) -> None:
    repo, cat_id, author_id = repo_pair
    eval_spec = EvalSpec(
        scenarios=[EvalScenario(description="d", input_context="c", success_criteria="s")]
    )
    skill = await repo.create(
        slug="versioned-skill",
        name="Versioned Skill",
        description="A versioned skill",
        content="Content for the versioned skill",
        category_id=cat_id,
        tags=[],
        version="2.0.0",
        author_id=author_id,
        dependencies=DependencyDeclaration(),
        eval_spec=eval_spec,
    )
    await repo.create_version(
        skill_id=skill.id,
        version="2.1.0",
        content="Updated content for version 2.1.0",
        dependencies=DependencyDeclaration(),
        eval_spec=eval_spec,
        author_id=author_id,
    )

    fetched = await repo.get_by_slug("versioned-skill", version="2.1.0")
    assert fetched is not None
    assert fetched.version == "2.1.0"

    default_fetched = await repo.get_by_slug("versioned-skill")
    assert default_fetched is not None


async def test_vector_search(repo_pair: tuple[SkillRepo, uuid.UUID, uuid.UUID]) -> None:
    repo, cat_id, author_id = repo_pair
    eval_spec = EvalSpec(
        scenarios=[EvalScenario(description="d", input_context="c", success_criteria="s")]
    )
    embedding = [0.1] * 1536
    await repo.create(
        slug="embedded-skill",
        name="Embedded Skill",
        description="A skill with an embedding",
        content="Content for the embedded skill",
        category_id=cat_id,
        tags=[],
        version="1.0.0",
        author_id=author_id,
        dependencies=DependencyDeclaration(),
        eval_spec=eval_spec,
        embedding=embedding,
    )

    results = await repo.vector_search(embedding, limit=10)
    assert len(results) >= 1
    assert any(s.slug == "embedded-skill" for s in results)


async def test_list_skills(repo_pair: tuple[SkillRepo, uuid.UUID, uuid.UUID]) -> None:
    repo, cat_id, author_id = repo_pair
    eval_spec = EvalSpec(
        scenarios=[EvalScenario(description="d", input_context="c", success_criteria="s")]
    )
    await repo.create(
        slug="list-skill-a",
        name="List Skill A",
        description="Skill A for listing",
        content="Content A for listing",
        category_id=cat_id,
        tags=[],
        version="1.0.0",
        author_id=author_id,
        dependencies=DependencyDeclaration(),
        eval_spec=eval_spec,
        trust_tier=TrustTier.COMMUNITY,
        cost_profile=CostProfile.FREE,
    )
    await repo.create(
        slug="list-skill-b",
        name="List Skill B",
        description="Skill B for listing",
        content="Content B for listing",
        category_id=cat_id,
        tags=[],
        version="1.0.0",
        author_id=author_id,
        dependencies=DependencyDeclaration(),
        eval_spec=eval_spec,
        trust_tier=TrustTier.EXPERIMENTAL,
        cost_profile=CostProfile.FREE,
    )

    all_skills = await repo.list_all()
    slugs = [s.slug for s in all_skills]
    assert "list-skill-a" in slugs
    assert "list-skill-b" in slugs
    assert all(isinstance(s, SkillSummary) for s in all_skills)

    community_skills = await repo.list_all(trust_tier=TrustTier.COMMUNITY)
    community_slugs = [s.slug for s in community_skills]
    assert "list-skill-a" in community_slugs
    assert "list-skill-b" not in community_slugs
