"""Capability repository with raw asyncpg SQL."""

import uuid as uuid_mod
from typing import Any

import asyncpg
import numpy as np
from asyncpg.exceptions import UniqueViolationError

from loom.models.capability import (
    Capability,
    CapabilityStep,
    CapabilitySummary,
    CapabilityVersion,
    DataFlowEdge,
)
from loom.models.common import (
    CostProfile,
    DependencyDeclaration,
    EvalSpec,
    Scope,
    TrustTier,
)

# Full column list for capabilities table
_CAPABILITY_COLUMNS = (
    "id, slug, name, description, category_id, tags, scope, "
    "version, author_id, trust_tier, steps, preconditions, "
    "expected_outcome, data_flow, dependencies, cost_profile, "
    "cost_drivers, estimated_duration, eval_spec, extends, "
    "embedding, eval_status, composite_score, created_at, updated_at"
)


def _to_vector(embedding: list[float] | None) -> np.ndarray | None:
    """Convert a list of floats to a numpy array for pgvector."""
    if embedding is None:
        return None
    return np.array(embedding, dtype=np.float32)


def _parse_steps(raw: list[dict[str, Any]]) -> list[CapabilityStep]:
    return [CapabilityStep(**s) for s in raw]


def _parse_data_flow(raw: list[dict[str, Any]] | None) -> list[DataFlowEdge]:
    if raw is None:
        return []
    return [DataFlowEdge(**e) for e in raw]


def _row_to_capability(row: asyncpg.Record) -> Capability:
    d = dict(row)
    embedding = d.get("embedding")
    if embedding is not None:
        d["embedding"] = list(embedding)
    d["steps"] = _parse_steps(d["steps"])
    d["preconditions"] = d.get("preconditions") or []
    d["expected_outcome"] = d.get("expected_outcome") or ""
    d["data_flow"] = _parse_data_flow(d.get("data_flow"))
    return Capability(**d)


def _row_to_summary(row: asyncpg.Record) -> CapabilitySummary:
    d = dict(row)
    return CapabilitySummary(
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
        step_count=d.get("step_count", 0),
    )


class CapabilityRepo:
    """Repository for capability persistence."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def create(
        self,
        *,
        slug: str,
        name: str,
        description: str,
        category_id: uuid_mod.UUID,
        tags: list[str],
        version: str,
        author_id: uuid_mod.UUID,
        steps: list[CapabilityStep],
        preconditions: list[str] | None = None,
        expected_outcome: str = "",
        data_flow: list[DataFlowEdge] | None = None,
        dependencies: DependencyDeclaration | None = None,
        eval_spec: EvalSpec | None = None,
        scope: Scope = Scope.COMMUNITY,
        trust_tier: TrustTier = TrustTier.EXPERIMENTAL,
        cost_profile: CostProfile = CostProfile.FREE,
        cost_drivers: list[str] | None = None,
        estimated_duration: str = "slow",
        extends: str | None = None,
        embedding: list[float] | None = None,
    ) -> Capability:
        """Insert a new capability and initial version record."""
        cost_drivers = cost_drivers or []
        preconditions = preconditions or []
        data_flow = data_flow or []
        deps = dependencies or DependencyDeclaration()
        espec = eval_spec or EvalSpec()

        steps_json = [s.model_dump() for s in steps]
        flow_json = [e.model_dump() for e in data_flow]
        deps_dict = deps.model_dump()
        eval_dict = espec.model_dump()

        try:
            async with self._conn.transaction():
                row = await self._conn.fetchrow(
                    f"""
                    INSERT INTO capabilities (
                        slug, name, description, category_id, tags, scope, version,
                        author_id, trust_tier, steps, preconditions, expected_outcome,
                        data_flow, dependencies, cost_profile, cost_drivers,
                        estimated_duration, eval_spec, extends, embedding
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7,
                        $8, $9, $10, $11, $12,
                        $13, $14, $15, $16,
                        $17, $18, $19, $20
                    )
                    RETURNING {_CAPABILITY_COLUMNS}
                    """,
                    slug,
                    name,
                    description,
                    category_id,
                    tags,
                    scope.value,
                    version,
                    author_id,
                    trust_tier.value,
                    steps_json,
                    preconditions,
                    expected_outcome,
                    flow_json,
                    deps_dict,
                    cost_profile.value,
                    cost_drivers,
                    estimated_duration,
                    eval_dict,
                    extends,
                    _to_vector(embedding),
                )

                capability = _row_to_capability(row)

                # Insert initial version record
                await self._conn.execute(
                    """
                    INSERT INTO capability_versions (
                        capability_id, version, steps, preconditions, expected_outcome,
                        data_flow, dependencies, cost_profile, cost_drivers,
                        estimated_duration, eval_spec, extends, author_id
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                    """,
                    capability.id,
                    version,
                    steps_json,
                    preconditions,
                    expected_outcome,
                    flow_json,
                    deps_dict,
                    cost_profile.value,
                    cost_drivers,
                    estimated_duration,
                    eval_dict,
                    extends,
                    author_id,
                )

        except UniqueViolationError:
            raise ValueError(f"Version '{version}' already exists for this capability") from None

        return capability

    async def get_by_slug(self, slug: str) -> Capability | None:
        """Return a capability by slug."""
        row = await self._conn.fetchrow(
            f"SELECT {_CAPABILITY_COLUMNS} FROM capabilities WHERE slug = $1",
            slug,
        )
        if row is None:
            return None
        return _row_to_capability(row)

    async def get_by_id(self, capability_id: uuid_mod.UUID) -> Capability | None:
        """Return a capability by id."""
        row = await self._conn.fetchrow(
            f"SELECT {_CAPABILITY_COLUMNS} FROM capabilities WHERE id = $1",
            capability_id,
        )
        if row is None:
            return None
        return _row_to_capability(row)

    async def update(
        self,
        capability_id: uuid_mod.UUID,
        *,
        version: str,
        author_id: uuid_mod.UUID,
        steps: list[CapabilityStep] | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        preconditions: list[str] | None = None,
        expected_outcome: str | None = None,
        data_flow: list[DataFlowEdge] | None = None,
        dependencies: DependencyDeclaration | None = None,
        cost_profile: CostProfile | None = None,
        cost_drivers: list[str] | None = None,
        estimated_duration: str | None = None,
        eval_spec: EvalSpec | None = None,
        extends: str | None = None,
        changelog: str | None = None,
        fields_set: set[str] | None = None,
    ) -> Capability | None:
        """Update a capability and create a version record."""
        set_parts: list[str] = ["version = $2"]
        params: list[Any] = [capability_id, version]

        def _add(field: str, value: object) -> None:
            if value is not None:
                params.append(value)
                set_parts.append(f"{field} = ${len(params)}")

        steps_json = [s.model_dump() for s in steps] if steps is not None else None
        flow_json = [e.model_dump() for e in data_flow] if data_flow is not None else None

        _add("steps", steps_json)
        _add("description", description)
        _add("tags", tags)
        _add("preconditions", preconditions)
        _add("expected_outcome", expected_outcome)
        _add("data_flow", flow_json)
        _add("dependencies", dependencies.model_dump() if dependencies else None)
        _add(
            "cost_profile",
            cost_profile.value if isinstance(cost_profile, CostProfile) else cost_profile,
        )
        _add("cost_drivers", cost_drivers)
        _add("estimated_duration", estimated_duration)
        _add("eval_spec", eval_spec.model_dump() if eval_spec else None)

        # For extends: support explicit clearing to NULL
        if extends is not None:
            _add("extends", extends)
        elif fields_set is not None and "extends" in fields_set:
            params.append(None)
            set_parts.append(f"extends = ${len(params)}")

        try:
            async with self._conn.transaction():
                row = await self._conn.fetchrow(
                    f"""
                    UPDATE capabilities SET {", ".join(set_parts)}, updated_at = now()
                    WHERE id = $1
                    RETURNING {_CAPABILITY_COLUMNS}
                    """,  # noqa: S608
                    *params,
                )
                if row is None:
                    return None

                updated = _row_to_capability(row)

                # Create version record from the updated state
                await self._conn.execute(
                    """
                    INSERT INTO capability_versions (
                        capability_id, version, steps, preconditions, expected_outcome,
                        data_flow, dependencies, cost_profile, cost_drivers,
                        estimated_duration, eval_spec, extends, author_id, changelog
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14
                    )
                    """,
                    updated.id,
                    version,
                    [s.model_dump() for s in updated.steps],
                    updated.preconditions,
                    updated.expected_outcome,
                    [e.model_dump() for e in updated.data_flow],
                    updated.dependencies.model_dump(),
                    updated.cost_profile.value,
                    updated.cost_drivers,
                    updated.estimated_duration,
                    updated.eval_spec.model_dump(),
                    updated.extends,
                    author_id,
                    changelog,
                )

        except UniqueViolationError:
            raise ValueError(f"Version '{version}' already exists for this capability") from None

        return updated

    async def list_all(
        self,
        category_id: uuid_mod.UUID | None = None,
        trust_tier: TrustTier | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CapabilitySummary]:
        """Return capability summaries, optionally filtered."""
        conditions: list[str] = []
        params: list[Any] = []

        if category_id is not None:
            params.append(category_id)
            conditions.append(f"category_id = ${len(params)}")

        if trust_tier is not None:
            params.append(trust_tier.value)
            conditions.append(f"trust_tier = ${len(params)}")

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)
        limit_param = f"${len(params)}"
        params.append(offset)
        offset_param = f"${len(params)}"
        rows = await self._conn.fetch(
            f"""
            SELECT id, slug, name, description, category_id, tags, version,
                   trust_tier, cost_profile, estimated_duration,
                   jsonb_array_length(steps) AS step_count
            FROM capabilities {where} ORDER BY name
            LIMIT {limit_param} OFFSET {offset_param}
            """,  # noqa: S608
            *params,
        )
        return [_row_to_summary(row) for row in rows]

    async def vector_search_summary(
        self,
        query_embedding: list[float],
        limit: int = 10,
        category_id: uuid_mod.UUID | None = None,
        trust_tier: TrustTier | None = None,
    ) -> list[CapabilitySummary]:
        """Return capability summaries ordered by vector similarity."""
        conditions: list[str] = ["embedding IS NOT NULL"]
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
            SELECT id, slug, name, description, category_id, tags, version,
                   trust_tier, cost_profile, estimated_duration,
                   jsonb_array_length(steps) AS step_count
            FROM capabilities {where}
            ORDER BY embedding <=> $1
            LIMIT ${len(params)}
            """,  # noqa: S608
            *params,
        )
        return [_row_to_summary(row) for row in rows]

    async def get_versions(self, capability_id: uuid_mod.UUID) -> list[CapabilityVersion]:
        """Return all versions for a capability, ordered by creation date."""
        rows = await self._conn.fetch(
            """
            SELECT id, capability_id, version, steps, preconditions,
                   expected_outcome, data_flow, dependencies, cost_profile,
                   cost_drivers, estimated_duration, eval_spec, extends,
                   author_id, changelog, created_at
            FROM capability_versions
            WHERE capability_id = $1
            ORDER BY created_at
            """,
            capability_id,
        )
        return [_row_to_version(row) for row in rows]

    async def get_version(
        self,
        capability_id: uuid_mod.UUID,
        version: str,
    ) -> CapabilityVersion | None:
        """Return a specific version of a capability."""
        row = await self._conn.fetchrow(
            """
            SELECT id, capability_id, version, steps, preconditions,
                   expected_outcome, data_flow, dependencies, cost_profile,
                   cost_drivers, estimated_duration, eval_spec, extends,
                   author_id, changelog, created_at
            FROM capability_versions
            WHERE capability_id = $1 AND version = $2
            """,
            capability_id,
            version,
        )
        if row is None:
            return None
        return _row_to_version(row)


def _row_to_version(row: asyncpg.Record) -> CapabilityVersion:
    d = dict(row)
    d["steps"] = _parse_steps(d["steps"])
    d["data_flow"] = _parse_data_flow(d.get("data_flow"))
    return CapabilityVersion(**d)
