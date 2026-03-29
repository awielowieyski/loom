"""Skill repository with raw asyncpg SQL."""

import json
import uuid as uuid_mod
from datetime import datetime
from typing import Any

import asyncpg
import numpy as np

from loom.db.repositories.service_metadata_repo import ServiceMetadataRepo
from loom.models.common import (
    AuthorshipStatus,
    CanonicalizationLevel,
    CostProfile,
    DependencyDeclaration,
    EvalSpec,
    LifecycleState,
    Scope,
    TrustTier,
)
from loom.models.skill import Skill, SkillSummary, SkillVersion

# Full column list for skills table
_SKILL_COLUMNS = (
    "id, slug, name, description, content, category_id, tags, scope, "
    "version, author_id, lifecycle_state, signature, trust_tier, cost_profile, "
    "cost_drivers, estimated_duration, dependencies, eval_spec, "
    "extends, embedding, current_version_id, published_version_id, provenance_summary, "
    "display_name, embedding_text, canonical_hash, execution_bundle_hash, "
    "canonicalization_level, authorship_status, change_type, change_agent, "
    "change_rationale, diff_summary, eval_status, composite_score, "
    "latest_eval_job_id, signature_key_fingerprint, "
    "source_uri, license, "
    "deprecated_at, successor_slug, stale_since, behavioral_score, "
    "last_eval_at, resolution_count, created_at, updated_at"
)

# Lighter column list for ranking / summary use — excludes content, embedding, eval_spec
_SUMMARY_COLUMNS = (
    "id, slug, name, description, category_id, tags, scope, version, "
    "author_id, trust_tier, cost_profile, cost_drivers, "
    "estimated_duration, dependencies, extends, created_at, updated_at"
)


def _to_vector(embedding: list[float] | None) -> np.ndarray | None:
    """Convert a list of floats to a numpy array for pgvector."""
    if embedding is None:
        return None
    return np.array(embedding, dtype=np.float32)


def _row_to_skill(row: asyncpg.Record) -> Skill:
    d = dict(row)
    # With register_vector, embedding comes back as numpy array
    embedding = d.get("embedding")
    if embedding is not None:
        if hasattr(embedding, "tolist"):
            d["embedding"] = embedding.tolist()
        elif isinstance(embedding, str):
            d["embedding"] = json.loads(embedding)
        else:
            d["embedding"] = list(embedding)
    # asyncpg returns JSONB as strings — parse them for Pydantic
    for key in ("dependencies", "eval_spec", "cost_drivers", "provenance_summary", "diff_summary"):
        val = d.get(key)
        if isinstance(val, str):
            d[key] = json.loads(val)
    latest_eval_job_id = d.get("latest_eval_job_id")
    if latest_eval_job_id is not None and not isinstance(latest_eval_job_id, str):
        d["latest_eval_job_id"] = str(latest_eval_job_id)
    return Skill(**d)


def _row_to_summary(row: asyncpg.Record) -> SkillSummary:
    """Build a SkillSummary from a row that has at least the summary columns."""
    d = dict(row)
    return SkillSummary(
        id=d["id"],
        slug=d["slug"],
        name=d["name"],
        description=d["description"],
        category_id=d["category_id"],
        tags=d["tags"],
        version=d["version"],
        trust_tier=d["trust_tier"],
        cost_profile=d["cost_profile"],
        estimated_duration=d["estimated_duration"],
    )


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
        source_uri: str | None = None,
        license: str | None = None,
        lifecycle_state: LifecycleState = LifecycleState.PUBLISHED,
        provenance_summary: dict[str, object] | None = None,
    ) -> Skill:
        """Insert a new skill and initial version record, returning the Skill."""
        cost_drivers = cost_drivers or []
        deps_dict = dependencies.model_dump()
        eval_dict = eval_spec.model_dump()
        provenance_json = provenance_summary or {}
        embedding_text = f"{name} — {description}".strip(" —")

        async with self._conn.transaction():
            row = await self._conn.fetchrow(
                """
                INSERT INTO skills (
                    slug, name, description, content, category_id, tags, scope, version,
                    author_id, lifecycle_state, signature, trust_tier, cost_profile, cost_drivers,
                    estimated_duration, dependencies, eval_spec, extends, embedding,
                    source_uri, license, provenance_summary, display_name, embedding_text,
                    canonicalization_level, authorship_status, change_type, change_agent,
                    change_rationale
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8,
                    $9, $10, $11, $12, $13, $14,
                    $15, $16, $17, $18, $19,
                    $20, $21, $22::jsonb, $23, $24,
                    $25, $26, $27, $28, $29
                )
                RETURNING id
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
                lifecycle_state.value,
                signature,
                trust_tier.value,
                cost_profile.value,
                cost_drivers,
                estimated_duration,
                deps_dict,
                eval_dict,
                extends,
                _to_vector(embedding),
                source_uri,
                license,
                json.dumps(provenance_json),
                name,
                embedding_text,
                CanonicalizationLevel.NONE.value,
                AuthorshipStatus.AUTHOR_OWNED.value,
                "author_submission"
                if lifecycle_state == LifecycleState.PUBLISHED
                else "source_import",
                f"author/{author_id}",
                "Initial skill creation",
            )
            skill_id = row["id"]

            version_row = await self._conn.fetchrow(
                """
                INSERT INTO skill_versions (
                    skill_id, version, content, dependencies, eval_spec,
                    cost_profile, cost_drivers, estimated_duration, extends,
                    signature, author_id, canonical_hash, display_name, embedding_text,
                    canonicalization_level, authorship_status, change_type, change_agent,
                    change_rationale
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                    $11, $12, $13, $14, $15, $16, $17, $18, $19
                )
                RETURNING id
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
                None,
                name,
                embedding_text,
                CanonicalizationLevel.NONE.value,
                AuthorshipStatus.AUTHOR_OWNED.value,
                "author_submission"
                if lifecycle_state == LifecycleState.PUBLISHED
                else "source_import",
                f"author/{author_id}",
                "Initial skill creation",
            )
            version_id = version_row["id"]
            published_version_id = (
                version_id if lifecycle_state == LifecycleState.PUBLISHED else None
            )
            await self._conn.execute(
                """
                UPDATE skills
                SET current_version_id = $2, published_version_id = $3
                WHERE id = $1
                """,
                skill_id,
                version_id,
                published_version_id,
            )

        skill = await self.get_by_id(skill_id)
        if skill is None:
            raise RuntimeError(f"Inserted skill {skill_id} could not be reloaded")
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

    async def set_version_pointers(
        self,
        skill_id: uuid_mod.UUID,
        *,
        current_version_id: uuid_mod.UUID,
        published_version_id: uuid_mod.UUID | None = None,
    ) -> None:
        """Update current and optionally published version pointers."""
        set_parts = ["current_version_id = $2"]
        params: list[Any] = [skill_id, current_version_id]
        if published_version_id is not None:
            params.append(published_version_id)
            set_parts.append(f"published_version_id = ${len(params)}")
        await self._conn.execute(
            f"UPDATE skills SET {', '.join(set_parts)} WHERE id = $1",  # noqa: S608
            *params,
        )

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
        dependencies: DependencyDeclaration | None = None,
        eval_spec: EvalSpec | None = None,
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
        _add("dependencies", dependencies.model_dump() if dependencies else None)
        _add("eval_spec", eval_spec.model_dump() if eval_spec else None)
        _add("extends", extends)

        row = await self._conn.fetchrow(
            f"""
            UPDATE skills SET {", ".join(set_parts)}, updated_at = now()
            WHERE id = $1
            RETURNING {_SKILL_COLUMNS}
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
                       s.lifecycle_state, s.current_version_id, s.published_version_id,
                       s.provenance_summary, s.display_name, s.embedding_text,
                       s.canonical_hash, s.execution_bundle_hash, s.canonicalization_level,
                       s.authorship_status, s.change_type, s.change_agent, s.change_rationale,
                       s.diff_summary, s.eval_status, s.composite_score, s.latest_eval_job_id,
                       s.signature_key_fingerprint, s.source_uri, s.license,
                       s.deprecated_at, s.successor_slug, s.stale_since, s.behavioral_score,
                       s.last_eval_at, s.resolution_count,
                       sv.id AS resolved_version_id,
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
                f"SELECT {_SKILL_COLUMNS} FROM skills WHERE slug = $1",
                slug,
            )
        if row is None:
            return None
        skill = _row_to_skill(row)
        row_data = dict(row)
        resolved_version_id = (
            row_data.get("resolved_version_id")
            or skill.published_version_id
            or skill.current_version_id
        )
        if resolved_version_id is None:
            return skill

        service_repo = ServiceMetadataRepo(self._conn)
        external_services = await service_repo.list_skill_external_services(resolved_version_id)
        pricing = await service_repo.list_pricing_facts(skill_version_id=resolved_version_id)
        setup_requirements = await service_repo.list_setup_requirements(
            skill_version_id=resolved_version_id
        )
        requires_paid_service = any(
            item.pricing_summary.get("pricing_model") not in (None, "free", "unknown")
            or item.pricing_summary.get("requires_paid_account") is True
            for item in external_services
        ) or any(f.pricing_model not in ("free", "unknown") for f in pricing)
        requires_network = bool(skill.dependencies.trust_requirements.network_access) or bool(
            external_services
        )
        return skill.model_copy(
            update={
                "external_services": external_services,
                "pricing": pricing,
                "setup_requirements": setup_requirements,
                "requires_paid_service": requires_paid_service,
                "requires_network": requires_network,
            }
        )

    async def get_by_id(self, skill_id: uuid_mod.UUID) -> Skill | None:
        """Return a skill by id."""
        row = await self._conn.fetchrow(
            f"SELECT {_SKILL_COLUMNS} FROM skills WHERE id = $1",
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

        conditions.append("lifecycle_state = 'published'")

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
        conditions: list[str] = ["embedding IS NOT NULL", "lifecycle_state = 'published'"]
        params: list[Any] = [np.array(query_embedding, dtype=np.float32)]

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
            SELECT {_SKILL_COLUMNS}
            FROM skills {where}
            ORDER BY embedding <=> $1
            LIMIT ${len(params)}
            """,  # noqa: S608
            *params,
        )
        return [_row_to_skill(row) for row in rows]

    async def vector_search_summary(
        self,
        query_embedding: list[float],
        limit: int = 10,
        category_id: uuid_mod.UUID | None = None,
        trust_tier: TrustTier | None = None,
    ) -> list[SkillSummary]:
        """Return skill summaries ordered by vector similarity (lightweight)."""
        conditions: list[str] = ["embedding IS NOT NULL", "lifecycle_state = 'published'"]
        params: list[Any] = [np.array(query_embedding, dtype=np.float32)]

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
            SELECT {_SUMMARY_COLUMNS}
            FROM skills {where}
            ORDER BY embedding <=> $1
            LIMIT ${len(params)}
            """,  # noqa: S608
            *params,
        )
        return [_row_to_summary(row) for row in rows]

    async def get_reeval_candidates(self, trust_tiers: list[str], limit: int) -> list[Skill]:
        """Return skills ordered by oldest last_eval_at, limited to N.

        Skills that have never been evaluated (last_eval_at IS NULL) are
        returned first, followed by skills with the oldest evaluation.
        """
        placeholders = ", ".join(f"${i + 1}" for i in range(len(trust_tiers)))
        params: list[Any] = [*trust_tiers, limit]
        rows = await self._conn.fetch(
            f"""
            SELECT {_SKILL_COLUMNS}
            FROM skills
            WHERE trust_tier IN ({placeholders})
              AND lifecycle_state = 'published'
            ORDER BY last_eval_at ASC NULLS FIRST
            LIMIT ${len(params)}
            """,  # noqa: S608
            *params,
        )
        return [_row_to_skill(row) for row in rows]

    async def count_by_trust_tiers(self, trust_tiers: list[str]) -> int:
        """Count skills in the given trust tiers."""
        placeholders = ", ".join(f"${i + 1}" for i in range(len(trust_tiers)))
        row = await self._conn.fetchrow(
            f"SELECT count(*) as cnt FROM skills WHERE trust_tier IN ({placeholders})",  # noqa: S608
            *trust_tiers,
        )
        return int(row["cnt"]) if row else 0

    async def update_eval_fields(
        self,
        skill_id: uuid_mod.UUID,
        eval_status: str,
        composite_score: float | None = None,
        latest_eval_job_id: uuid_mod.UUID | None = None,
        behavioral_score: float | None = None,
        last_eval_at: datetime | None = None,
    ) -> None:
        """Update evaluation-related fields on a skill row."""
        set_parts = ["eval_status = $1", "updated_at = now()"]
        params: list[Any] = [eval_status]

        if composite_score is not None:
            params.append(composite_score)
            set_parts.append(f"composite_score = ${len(params)}")

        if latest_eval_job_id is not None:
            params.append(latest_eval_job_id)
            set_parts.append(f"latest_eval_job_id = ${len(params)}")

        if behavioral_score is not None:
            params.append(behavioral_score)
            set_parts.append(f"behavioral_score = ${len(params)}")

        if last_eval_at is not None:
            params.append(last_eval_at)
            set_parts.append(f"last_eval_at = ${len(params)}")

        params.append(skill_id)
        await self._conn.execute(
            f"UPDATE skills SET {', '.join(set_parts)} WHERE id = ${len(params)}",  # noqa: S608
            *params,
        )

    async def update_trust_tier(self, skill_id: uuid_mod.UUID, trust_tier: TrustTier) -> None:
        """Promote or demote a skill's trust tier."""
        await self._conn.execute(
            "UPDATE skills SET trust_tier = $1, updated_at = now() WHERE id = $2",
            trust_tier.value,
            skill_id,
        )

    async def update_metadata(
        self,
        skill_id: uuid_mod.UUID,
        *,
        name: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        embedding: list[float] | None = None,
        embedding_text: str | None = None,
        eval_spec: EvalSpec | None = None,
        lifecycle_state: LifecycleState | None = None,
        provenance_summary: dict[str, object] | None = None,
        canonicalization_level: CanonicalizationLevel | None = None,
        authorship_status: AuthorshipStatus | None = None,
        change_type: str | None = None,
        change_agent: str | None = None,
        change_rationale: str | None = None,
    ) -> None:
        """Update searchable metadata fields (used by vetting pipeline)."""
        set_parts: list[str] = ["updated_at = now()"]
        params: list[Any] = []

        if name is not None:
            params.append(name)
            set_parts.append(f"name = ${len(params)}")
        if description is not None:
            params.append(description)
            set_parts.append(f"description = ${len(params)}")
        if tags is not None:
            params.append(tags)
            set_parts.append(f"tags = ${len(params)}")
        if embedding is not None:
            params.append(_to_vector(embedding))
            set_parts.append(f"embedding = ${len(params)}::vector")
        if embedding_text is not None:
            params.append(embedding_text)
            set_parts.append(f"embedding_text = ${len(params)}")
        if eval_spec is not None:
            params.append(json.dumps(eval_spec.model_dump(mode="json")))
            set_parts.append(f"eval_spec = ${len(params)}::jsonb")
        if lifecycle_state is not None:
            params.append(lifecycle_state.value)
            set_parts.append(f"lifecycle_state = ${len(params)}")
        if provenance_summary is not None:
            params.append(json.dumps(provenance_summary))
            set_parts.append(f"provenance_summary = ${len(params)}::jsonb")
        if canonicalization_level is not None:
            params.append(canonicalization_level.value)
            set_parts.append(f"canonicalization_level = ${len(params)}")
        if authorship_status is not None:
            params.append(authorship_status.value)
            set_parts.append(f"authorship_status = ${len(params)}")
        if change_type is not None:
            params.append(change_type)
            set_parts.append(f"change_type = ${len(params)}")
        if change_agent is not None:
            params.append(change_agent)
            set_parts.append(f"change_agent = ${len(params)}")
        if change_rationale is not None:
            params.append(change_rationale)
            set_parts.append(f"change_rationale = ${len(params)}")

        if len(params) == 0:
            return  # nothing to update

        if name is not None:
            params.append(name)
            set_parts.append(f"display_name = ${len(params)}")

        params.append(skill_id)
        await self._conn.execute(
            f"UPDATE skills SET {', '.join(set_parts)} WHERE id = ${len(params)}",  # noqa: S608
            *params,
        )

    # --- M4: Living registry lifecycle methods ---

    async def increment_resolution_count(self, skill_id: uuid_mod.UUID) -> None:
        """Atomically increment the resolution_count for a skill."""
        await self._conn.execute(
            "UPDATE skills SET resolution_count = resolution_count + 1 WHERE id = $1",
            skill_id,
        )

    async def mark_stale(self, skill_id: uuid_mod.UUID) -> None:
        """Set stale_since to now() for a skill that isn't already stale."""
        await self._conn.execute(
            "UPDATE skills SET stale_since = now() WHERE id = $1 AND stale_since IS NULL",
            skill_id,
        )

    async def clear_stale(self, skill_id: uuid_mod.UUID) -> None:
        """Clear stale_since when a skill gets new usage."""
        await self._conn.execute(
            "UPDATE skills SET stale_since = NULL WHERE id = $1",
            skill_id,
        )

    async def mark_deprecated(self, skill_id: uuid_mod.UUID, successor_slug: str | None) -> None:
        """Set deprecated_at and successor_slug on a skill."""
        await self._conn.execute(
            "UPDATE skills SET deprecated_at = now(), successor_slug = $2 WHERE id = $1",
            skill_id,
            successor_slug,
        )

    async def get_stale_candidates(self, staleness_window_days: int) -> list[uuid_mod.UUID]:
        """Find skills with 0 usage reports in the time window, not already stale."""
        rows = await self._conn.fetch(
            """SELECT s.id FROM skills s
               LEFT JOIN usage_reports ur ON ur.skill_id = s.id
                 AND ur.created_at >= now() - ($1 || ' days')::interval
               WHERE ur.id IS NULL
                 AND s.stale_since IS NULL
                 AND s.created_at < now() - ($1 || ' days')::interval""",
            str(staleness_window_days),
        )
        return [row["id"] for row in rows]

    async def get_unevaluated(self, limit: int = 50) -> list[Skill]:
        """Return skills that have never been evaluated, ordered by creation date."""
        rows = await self._conn.fetch(
            f"""
            SELECT {_SKILL_COLUMNS}
            FROM skills
            WHERE (eval_status IS NULL OR eval_status = 'pending')
              AND lifecycle_state = 'published'
            ORDER BY created_at ASC
            LIMIT $1
            """,
            limit,
        )
        return [_row_to_skill(row) for row in rows]

    async def get_by_source_pattern(self, pattern: str, limit: int = 50) -> list[Skill]:
        """Return skills whose source_uri matches an ILIKE pattern."""
        escaped = pattern.replace("%", "\\%").replace("_", "\\_")
        rows = await self._conn.fetch(
            f"""
            SELECT {_SKILL_COLUMNS}
            FROM skills
            WHERE source_uri ILIKE $1
            ORDER BY created_at ASC
            LIMIT $2
            """,
            f"%{escaped}%",
            limit,
        )
        return [_row_to_skill(row) for row in rows]
