"""Repository for external service and pricing metadata."""

import uuid as uuid_mod
from datetime import UTC, datetime
from typing import Any

import asyncpg

from loom.models.service_metadata import (
    ExternalService,
    PricingFact,
    PricingFactWrite,
    ServiceDependencyWrite,
    ServiceSetupRequirement,
    ServiceSetupRequirementWrite,
    SkillExternalService,
)


def _coerce_json(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    return value


class ServiceMetadataRepo:
    """Persistence for revision-scoped service metadata and pricing evidence."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def list_skill_external_services(
        self, skill_version_id: uuid_mod.UUID
    ) -> list[SkillExternalService]:
        rows = await self._conn.fetch(
            """
            SELECT
                d.id,
                d.skill_version_id,
                d.service_id,
                d.required,
                d.dependency_role,
                d.operations,
                d.pricing_summary,
                d.evidence_summary,
                d.created_at,
                s.id AS service_row_id,
                s.service_key,
                s.display_name,
                s.vendor_name,
                s.service_type,
                s.homepage_url,
                s.docs_url,
                s.pricing_url,
                s.default_auth_methods,
                s.default_env_vars,
                s.metadata AS service_metadata,
                s.created_at AS service_created_at,
                s.updated_at AS service_updated_at
            FROM skill_service_dependencies d
            JOIN external_services s ON s.id = d.service_id
            WHERE d.skill_version_id = $1
            ORDER BY d.created_at ASC, s.display_name ASC
            """,
            skill_version_id,
        )
        items: list[SkillExternalService] = []
        for row in rows:
            data = dict(row)
            service = ExternalService(
                id=data["service_row_id"],
                service_key=data["service_key"],
                display_name=data["display_name"],
                vendor_name=data["vendor_name"],
                service_type=data["service_type"],
                homepage_url=data["homepage_url"],
                docs_url=data["docs_url"],
                pricing_url=data["pricing_url"],
                default_auth_methods=_coerce_json(data.get("default_auth_methods"), []),
                default_env_vars=_coerce_json(data.get("default_env_vars"), []),
                metadata=_coerce_json(data.get("service_metadata"), {}),
                created_at=data["service_created_at"],
                updated_at=data["service_updated_at"],
            )
            items.append(
                SkillExternalService(
                    id=data["id"],
                    skill_version_id=data["skill_version_id"],
                    service_id=data["service_id"],
                    required=data["required"],
                    dependency_role=data["dependency_role"],
                    operations=_coerce_json(data.get("operations"), []),
                    pricing_summary=_coerce_json(data.get("pricing_summary"), {}),
                    evidence_summary=_coerce_json(data.get("evidence_summary"), {}),
                    created_at=data["created_at"],
                    service=service,
                )
            )
        return items

    async def list_pricing_facts(self, *, skill_version_id: uuid_mod.UUID) -> list[PricingFact]:
        rows = await self._conn.fetch(
            """
            SELECT *
            FROM pricing_facts
            WHERE subject_kind = 'skill_version'
              AND subject_id = $1
              AND superseded_by IS NULL
            ORDER BY observed_at DESC, created_at DESC
            """,
            skill_version_id,
        )
        return [
            PricingFact(
                **{
                    **dict(row),
                    "price_structured": _coerce_json(row["price_structured"], {}),
                }
            )
            for row in rows
        ]

    async def list_setup_requirements(
        self, *, skill_version_id: uuid_mod.UUID
    ) -> list[ServiceSetupRequirement]:
        rows = await self._conn.fetch(
            """
            SELECT *
            FROM service_setup_requirements
            WHERE skill_version_id = $1
            ORDER BY created_at ASC
            """,
            skill_version_id,
        )
        return [
            ServiceSetupRequirement(
                **{
                    **dict(row),
                    "evidence_summary": _coerce_json(row["evidence_summary"], {}),
                }
            )
            for row in rows
        ]

    async def ensure_service(self, data: ServiceDependencyWrite) -> ExternalService:
        row = await self._conn.fetchrow(
            """
            INSERT INTO external_services (
                service_key,
                display_name,
                vendor_name,
                service_type,
                homepage_url,
                docs_url,
                pricing_url,
                default_auth_methods,
                default_env_vars,
                metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9::jsonb, $10::jsonb)
            ON CONFLICT (service_key) DO UPDATE SET
                display_name = COALESCE(excluded.display_name, external_services.display_name),
                vendor_name = COALESCE(excluded.vendor_name, external_services.vendor_name),
                service_type = COALESCE(excluded.service_type, external_services.service_type),
                homepage_url = COALESCE(excluded.homepage_url, external_services.homepage_url),
                docs_url = COALESCE(excluded.docs_url, external_services.docs_url),
                pricing_url = COALESCE(excluded.pricing_url, external_services.pricing_url),
                default_auth_methods = CASE
                    WHEN jsonb_array_length(excluded.default_auth_methods) > 0
                    THEN excluded.default_auth_methods
                    ELSE external_services.default_auth_methods
                END,
                default_env_vars = CASE
                    WHEN jsonb_array_length(excluded.default_env_vars) > 0
                    THEN excluded.default_env_vars
                    ELSE external_services.default_env_vars
                END,
                metadata = CASE
                    WHEN excluded.metadata <> '{}'::jsonb
                    THEN excluded.metadata
                    ELSE external_services.metadata
                END,
                updated_at = now()
            RETURNING *
            """,
            data.service_key,
            data.display_name,
            data.vendor_name,
            data.service_type,
            data.homepage_url,
            data.docs_url,
            data.pricing_url,
            data.default_auth_methods,
            data.default_env_vars,
            data.metadata,
        )
        assert row is not None
        return ExternalService(
            **{
                **dict(row),
                "default_auth_methods": _coerce_json(row["default_auth_methods"], []),
                "default_env_vars": _coerce_json(row["default_env_vars"], []),
                "metadata": _coerce_json(row["metadata"], {}),
            }
        )

    async def replace_skill_version_metadata(
        self,
        *,
        skill_version_id: uuid_mod.UUID,
        dependencies: list[ServiceDependencyWrite],
        pricing_facts: list[PricingFactWrite],
        setup_requirements: list[ServiceSetupRequirementWrite],
    ) -> None:
        async with self._conn.transaction():
            await self._conn.execute(
                "DELETE FROM service_setup_requirements WHERE skill_version_id = $1",
                skill_version_id,
            )
            await self._conn.execute(
                "DELETE FROM skill_service_dependencies WHERE skill_version_id = $1",
                skill_version_id,
            )
            await self._conn.execute(
                """
                DELETE FROM pricing_facts
                WHERE subject_kind = 'skill_version'
                  AND subject_id = $1
                  AND source_kind = 'artifact'
                """,
                skill_version_id,
            )

            service_ids: dict[str, uuid_mod.UUID] = {}
            for dependency in dependencies:
                service = await self.ensure_service(dependency)
                service_ids[dependency.service_key] = service.id
                await self._conn.execute(
                    """
                    INSERT INTO skill_service_dependencies (
                        skill_version_id,
                        service_id,
                        required,
                        dependency_role,
                        operations,
                        pricing_summary,
                        evidence_summary
                    ) VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7::jsonb)
                    """,
                    skill_version_id,
                    service.id,
                    dependency.required,
                    dependency.dependency_role,
                    dependency.operations,
                    dependency.pricing_summary,
                    dependency.evidence_summary,
                )

            for requirement in setup_requirements:
                service_id = service_ids.get(requirement.service_key)
                if service_id is None:
                    continue
                await self._conn.execute(
                    """
                    INSERT INTO service_setup_requirements (
                        skill_version_id,
                        service_id,
                        requirement_type,
                        key,
                        value_hint,
                        required,
                        instructions,
                        evidence_summary
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb)
                    """,
                    skill_version_id,
                    service_id,
                    requirement.requirement_type,
                    requirement.key,
                    requirement.value_hint,
                    requirement.required,
                    requirement.instructions,
                    requirement.evidence_summary,
                )

            now = datetime.now(UTC)
            for fact in pricing_facts:
                await self._conn.execute(
                    """
                    INSERT INTO pricing_facts (
                        subject_kind,
                        subject_id,
                        fact_type,
                        pricing_model,
                        operation_name,
                        unit_name,
                        unit_cost_usd,
                        currency,
                        price_text_raw,
                        price_structured,
                        source_kind,
                        source_artifact_id,
                        source_uri,
                        evidence_snippet,
                        confidence,
                        observed_at
                    ) VALUES (
                        'skill_version',
                        $1,
                        $2,
                        $3,
                        $4,
                        $5,
                        $6,
                        $7,
                        $8,
                        $9::jsonb,
                        $10,
                        $11,
                        $12,
                        $13,
                        $14,
                        $15
                    )
                    """,
                    skill_version_id,
                    fact.fact_type,
                    fact.pricing_model,
                    fact.operation_name,
                    fact.unit_name,
                    fact.unit_cost_usd,
                    fact.currency,
                    fact.price_text_raw,
                    fact.price_structured,
                    fact.source_kind,
                    fact.source_artifact_id,
                    fact.source_uri,
                    fact.evidence_snippet,
                    fact.confidence,
                    fact.observed_at or now,
                )
