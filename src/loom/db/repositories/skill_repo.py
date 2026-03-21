"""Skill repository with raw asyncpg SQL."""

import uuid as uuid_mod
from typing import Any

import asyncpg

from loom.models.common import CostProfile, DependencyDeclaration, EvalSpec, Scope, TrustTier
from loom.models.skill import Skill, SkillSummary, SkillVersion


def _row_to_skill(row: asyncpg.Record) -> Skill:
    d = dict(row)
    # Vector comes back as a string or list; normalise to list[float]
    embedding = d.get("embedding")
    if embedding is not None and not isinstance(embedding, list):
        embedding = [float(x) for x in str(embedding).strip("[]").split(",")]
    d["embedding"] = embedding
    return Skill(**d)


class SkillRepo:
    """Repository for skill persistence."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def create(
        self,
        *,
        slug: str,
        name: str,
        description: str,
        content: str,
        category_id: uuid_mod.UUID,
        tags: list[str],
        version: str,
        author_id: uuid_mod.UUID,
        dependencies: DependencyDeclaration,
        eval_spec: EvalSpec,
        scope: Scope = Scope.COMMUNITY,
        trust_tier: TrustTier = TrustTier.EXPERIMENTAL,
        cost_profile: CostProfile = CostProfile.FREE,
        cost_drivers: list[str] | None = None,
        estimated_duration: str = "fast",
        extends: str | None = None,
        signature: str | None = None,
        embedding: list[float] | None = None,
    ) -> Skill:
        """Insert a new skill and initial version record, returning the Skill."""
        cost_drivers = cost_drivers or []
        deps_dict = dependencies.model_dump()
        eval_dict = eval_spec.model_dump()

        # Insert skill row
        row = await self._conn.fetchrow(
            """
            INSERT INTO skills (
                slug, name, description, content, category_id, tags, scope, version,
                author_id, signature, trust_tier, cost_profile, cost_drivers,
                estimated_duration, dependencies, eval_spec, extends, embedding
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8,
                $9, $10, $11, $12, $13,
                $14, $15, $16, $17, $18::vector
            )
            RETURNING id, slug, name, description, content, category_id, tags, scope,
                      version, author_id, signature, trust_tier, cost_profile,
                      cost_drivers, estimated_duration, dependencies, eval_spec,
                      extends, embedding, created_at, updated_at
            """,
            slug,
            name,
            description,
            content,
            category_id,
            tags,
            scope.value,
            version,
            author_id,
            signature,
            trust_tier.value,
            cost_profile.value,
            cost_drivers,
            estimated_duration,
            deps_dict,
            eval_dict,
            extends,
            str(embedding) if embedding is not None else None,
        )

        skill = _row_to_skill(row)

        # Insert initial skill_version record
        await self._conn.execute(
            """
            INSERT INTO skill_versions (
                skill_id, version, content, dependencies, eval_spec,
                cost_profile, cost_drivers, estimated_duration, extends,
                signature, author_id
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
            skill.id,
            version,
            content,
            deps_dict,
            eval_dict,
            cost_profile.value,
            cost_drivers,
            estimated_duration,
            extends,
            signature,
            author_id,
        )

        return skill

    async def create_version(
        self,
        *,
        skill_id: uuid_mod.UUID,
        version: str,
        content: str,
        dependencies: DependencyDeclaration,
        eval_spec: EvalSpec,
        author_id: uuid_mod.UUID,
        cost_profile: CostProfile = CostProfile.FREE,
        cost_drivers: list[str] | None = None,
        estimated_duration: str = "fast",
        extends: str | None = None,
        signature: str | None = None,
        changelog: str | None = None,
    ) -> SkillVersion:
        """Insert a new version row and return it."""
        cost_drivers = cost_drivers or []
        deps_dict = dependencies.model_dump()
        eval_dict = eval_spec.model_dump()

        row = await self._conn.fetchrow(
            """
            INSERT INTO skill_versions (
                skill_id, version, content, dependencies, eval_spec,
                cost_profile, cost_drivers, estimated_duration, extends,
                signature, author_id, changelog
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            RETURNING id, skill_id, version, content, dependencies, eval_spec,
                      cost_profile, cost_drivers, estimated_duration, extends,
                      signature, author_id, changelog, created_at
            """,
            skill_id,
            version,
            content,
            deps_dict,
            eval_dict,
            cost_profile.value,
            cost_drivers,
            estimated_duration,
            extends,
            signature,
            author_id,
            changelog,
        )
        return SkillVersion(**dict(row))

    async def update(
        self,
        skill_id: uuid_mod.UUID,
        *,
        version: str,
        content: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        cost_profile: CostProfile | None = None,
        cost_drivers: list[str] | None = None,
        estimated_duration: str | None = None,
        dependencies: dict[str, object] | None = None,
        eval_spec: dict[str, object] | None = None,
        extends: str | None = None,
    ) -> Skill | None:
        """UPDATE skills SET ... WHERE id = $1, RETURNING *."""
        set_parts: list[str] = ["version = $2"]
        params: list[Any] = [skill_id, version]

        def _add(field: str, value: object) -> None:
            if value is not None:
                params.append(value)
                set_parts.append(f"{field} = ${len(params)}")

        _add("content", content)
        _add("description", description)
        _add("tags", tags)
        _add(
            "cost_profile",
            cost_profile.value if isinstance(cost_profile, CostProfile) else cost_profile,
        )
        _add("cost_drivers", cost_drivers)
        _add("estimated_duration", estimated_duration)
        _add("dependencies", dependencies)
        _add("eval_spec", eval_spec)
        _add("extends", extends)

        row = await self._conn.fetchrow(
            f"""
            UPDATE skills SET {", ".join(set_parts)}, updated_at = now()
            WHERE id = $1
            RETURNING id, slug, name, description, content, category_id, tags, scope,
                      version, author_id, signature, trust_tier, cost_profile,
                      cost_drivers, estimated_duration, dependencies, eval_spec,
                      extends, embedding, created_at, updated_at
            """,  # noqa: S608
            *params,
        )
        if row is None:
            return None
        return _row_to_skill(row)

    async def get_by_slug(self, slug: str, version: str | None = None) -> Skill | None:
        """Return a skill by slug (optionally at a specific version)."""
        if version is not None:
            row = await self._conn.fetchrow(
                """
                SELECT s.id, s.slug, s.name, s.description, s.category_id,
                       s.tags, s.scope, s.author_id, s.signature, s.trust_tier,
                       s.embedding, s.created_at, s.updated_at,
                       sv.version, sv.content, sv.dependencies, sv.eval_spec,
                       sv.cost_profile, sv.cost_drivers, sv.estimated_duration, sv.extends
                FROM skills s
                JOIN skill_versions sv ON sv.skill_id = s.id
                WHERE s.slug = $1 AND sv.version = $2
                """,
                slug,
                version,
            )
        else:
            row = await self._conn.fetchrow(
                """
                SELECT id, slug, name, description, content, category_id, tags, scope,
                       version, author_id, signature, trust_tier, cost_profile,
                       cost_drivers, estimated_duration, dependencies, eval_spec,
                       extends, embedding, created_at, updated_at
                FROM skills WHERE slug = $1
                """,
                slug,
            )
        if row is None:
            return None
        return _row_to_skill(row)

    async def get_by_id(self, skill_id: uuid_mod.UUID) -> Skill | None:
        """Return a skill by id."""
        row = await self._conn.fetchrow(
            """
            SELECT id, slug, name, description, content, category_id, tags, scope,
                   version, author_id, signature, trust_tier, cost_profile,
                   cost_drivers, estimated_duration, dependencies, eval_spec,
                   extends, embedding, created_at, updated_at
            FROM skills WHERE id = $1
            """,
            skill_id,
        )
        if row is None:
            return None
        return _row_to_skill(row)

    async def list_all(
        self,
        category_id: uuid_mod.UUID | None = None,
        trust_tier: TrustTier | None = None,
    ) -> list[SkillSummary]:
        """Return skill summaries, optionally filtered."""
        conditions: list[str] = []
        params: list[Any] = []

        if category_id is not None:
            params.append(category_id)
            conditions.append(f"category_id = ${len(params)}")

        if trust_tier is not None:
            params.append(trust_tier.value)
            conditions.append(f"trust_tier = ${len(params)}")

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = await self._conn.fetch(
            f"""
            SELECT id, slug, name, description, category_id, tags, version,
                   trust_tier, cost_profile, estimated_duration
            FROM skills {where} ORDER BY name
            """,  # noqa: S608
            *params,
        )
        return [SkillSummary(**dict(row)) for row in rows]

    async def vector_search(
        self,
        query_embedding: list[float],
        limit: int = 10,
        category_id: uuid_mod.UUID | None = None,
        trust_tier: TrustTier | None = None,
    ) -> list[Skill]:
        """Return skills ordered by vector similarity."""
        conditions: list[str] = ["embedding IS NOT NULL"]
        params: list[Any] = [str(query_embedding)]

        if category_id is not None:
            params.append(category_id)
            conditions.append(f"category_id = ${len(params)}")

        if trust_tier is not None:
            params.append(trust_tier.value)
            conditions.append(f"trust_tier = ${len(params)}")

        params.append(limit)
        where = f"WHERE {' AND '.join(conditions)}"
        rows = await self._conn.fetch(
            f"""
            SELECT id, slug, name, description, content, category_id, tags, scope,
                   version, author_id, signature, trust_tier, cost_profile,
                   cost_drivers, estimated_duration, dependencies, eval_spec,
                   extends, embedding, created_at, updated_at
            FROM skills {where}
            ORDER BY embedding <=> $1::vector
            LIMIT ${len(params)}
            """,  # noqa: S608
            *params,
        )
        return [_row_to_skill(row) for row in rows]
