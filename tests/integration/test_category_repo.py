"""Integration tests for CategoryRepo."""

import asyncpg
import pytest

from loom.db.repositories.category_repo import CategoryRepo
from loom.models.category import CategoryCreate


@pytest.fixture
def repo(db_conn: asyncpg.Connection) -> CategoryRepo:
    return CategoryRepo(db_conn)


async def test_create_and_get_by_slug(repo: CategoryRepo) -> None:
    data = CategoryCreate(slug="test-cat", name="Test Category", description="A test")
    created = await repo.create(data)
    assert created.id is not None
    assert created.slug == "test-cat"

    fetched = await repo.get_by_slug("test-cat")
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.name == "Test Category"


async def test_get_by_slug_missing(repo: CategoryRepo) -> None:
    result = await repo.get_by_slug("does-not-exist")
    assert result is None


async def test_get_by_id(repo: CategoryRepo) -> None:
    data = CategoryCreate(slug="cat-by-id", name="Cat By Id")
    created = await repo.create(data)

    fetched = await repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.slug == "cat-by-id"


async def test_list_all(repo: CategoryRepo) -> None:
    await repo.create(CategoryCreate(slug="list-cat-1", name="List Cat 1"))
    await repo.create(CategoryCreate(slug="list-cat-2", name="List Cat 2"))

    results = await repo.list_all()
    slugs = [r.slug for r in results]
    assert "list-cat-1" in slugs
    assert "list-cat-2" in slugs


async def test_create_child_category(repo: CategoryRepo) -> None:
    parent = await repo.create(CategoryCreate(slug="parent-cat", name="Parent"))
    child = await repo.create(CategoryCreate(slug="child-cat", name="Child", parent_id=parent.id))

    assert child.parent_id == parent.id
    fetched = await repo.get_by_slug("child-cat")
    assert fetched is not None
    assert fetched.parent_id == parent.id
