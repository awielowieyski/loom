"""Category repository with raw asyncpg SQL."""

import uuid as uuid_mod

import asyncpg

from loom.models.category import Category, CategoryCreate


class CategoryRepo:
    """Repository for category persistence."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def create(self, data: CategoryCreate) -> Category:
        """Insert a new category and return the created record."""
        row = await self._conn.fetchrow(
            """
            INSERT INTO categories (slug, name, description, parent_id)
            VALUES ($1, $2, $3, $4)
            RETURNING id, slug, name, description, parent_id, created_at
            """,
            data.slug,
            data.name,
            data.description,
            data.parent_id,
        )
        return Category(**dict(row))

    async def get_by_slug(self, slug: str) -> Category | None:
        """Return a category by slug, or None if not found."""
        row = await self._conn.fetchrow(
            "SELECT id, slug, name, description, parent_id, created_at"
            " FROM categories WHERE slug = $1",
            slug,
        )
        if row is None:
            return None
        return Category(**dict(row))

    async def get_by_id(self, category_id: uuid_mod.UUID) -> Category | None:
        """Return a category by id, or None if not found."""
        row = await self._conn.fetchrow(
            "SELECT id, slug, name, description, parent_id, created_at"
            " FROM categories WHERE id = $1",
            category_id,
        )
        if row is None:
            return None
        return Category(**dict(row))

    async def list_all(self) -> list[Category]:
        """Return all categories."""
        rows = await self._conn.fetch(
            "SELECT id, slug, name, description, parent_id, created_at"
            " FROM categories ORDER BY name"
        )
        return [Category(**dict(row)) for row in rows]
