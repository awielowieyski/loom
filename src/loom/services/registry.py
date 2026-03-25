"""RegistryService: create, retrieve and list skills."""

import uuid as uuid_mod

from loom.db.repositories.category_repo import CategoryRepo
from loom.db.repositories.skill_repo import SkillRepo
from loom.models.common import (
    CostProfile,
    EstimatedDuration,
    Scope,
    TrustTier,
)
from loom.models.skill import Skill, SkillCreate, SkillSummary, SkillUpdate
from loom.services.eval import EvalService


def _coerce_duration(value: EstimatedDuration | str | None, fallback: str) -> str:
    """Safely extract a string value from an EstimatedDuration, str, or None."""
    if value is None:
        return fallback
    return value.value if isinstance(value, EstimatedDuration) else str(value)


def _coerce_cost_profile(value: CostProfile | str | None, fallback: CostProfile) -> CostProfile:
    """Coerce a CostProfile value, returning the fallback when None."""
    if value is None:
        return fallback
    return value if isinstance(value, CostProfile) else CostProfile(value)


def _coerce_scope(value: Scope | str) -> str:
    """Extract the string value from a Scope enum or pass through."""
    return value.value if isinstance(value, Scope) else str(value)


class RegistryService:
    """Orchestrates skill registration with structural validation."""

    def __init__(
        self,
        skill_repo: SkillRepo,
        category_repo: CategoryRepo,
        eval_service: EvalService,
    ) -> None:
        self._skill_repo = skill_repo
        self._category_repo = category_repo
        self._eval_service = eval_service

    async def create_skill(
        self,
        data: SkillCreate,
        author_id: uuid_mod.UUID,
        embedding: list[float] | None = None,
    ) -> Skill:
        """Validate, resolve category, then create skill + initial version."""
        # Structural validation
        result = self._eval_service.validate_structure(data)
        if not result.passed:
            raise ValueError(f"Validation failed: {'; '.join(result.errors)}")

        # Resolve category
        category = await self._category_repo.get_by_slug(data.category_slug)
        if category is None:
            raise ValueError(f"Category not found: {data.category_slug!r}")

        # Create skill (also creates initial skill_version)
        return await self._skill_repo.create(
            slug=data.slug,
            name=data.name,
            description=data.description,
            content=data.content,
            category_id=category.id,
            tags=data.tags,
            version=data.version,
            author_id=author_id,
            dependencies=data.dependencies,
            eval_spec=data.eval_spec,
            scope=data.scope,
            trust_tier=data.trust_tier,
            cost_profile=data.cost_profile,
            cost_drivers=data.cost_drivers,
            estimated_duration=_coerce_duration(data.estimated_duration, "fast"),
            extends=data.extends,
            embedding=embedding,
            source_uri=data.source_uri,
            license=data.license,
        )

    async def update_skill(
        self,
        slug: str,
        data: SkillUpdate,
        author_id: uuid_mod.UUID,
    ) -> Skill:
        """Merge new values over existing skill, update skills table, create version record."""
        existing = await self._skill_repo.get_by_slug(slug)
        if existing is None:
            raise ValueError(f"Skill not found: {slug!r}")

        # Merge: new values override existing where provided
        content = data.content if data.content is not None else existing.content
        description = data.description if data.description is not None else existing.description
        tags = data.tags if data.tags is not None else existing.tags
        cost_profile_enum = _coerce_cost_profile(data.cost_profile, existing.cost_profile)
        cost_drivers = data.cost_drivers if data.cost_drivers is not None else existing.cost_drivers
        estimated_duration_val = _coerce_duration(
            data.estimated_duration, existing.estimated_duration
        )
        dependencies = data.dependencies if data.dependencies is not None else existing.dependencies
        eval_spec = data.eval_spec if data.eval_spec is not None else existing.eval_spec
        extends = data.extends if data.extends is not None else existing.extends

        updated = await self._skill_repo.update(
            existing.id,
            version=data.version,
            content=content,
            description=description,
            tags=tags,
            cost_profile=cost_profile_enum,
            cost_drivers=cost_drivers,
            estimated_duration=estimated_duration_val,
            dependencies=dependencies,
            eval_spec=eval_spec,
            extends=extends,
        )
        if updated is None:
            raise ValueError(f"Update failed for skill: {slug!r}")

        await self._skill_repo.create_version(
            skill_id=existing.id,
            version=data.version,
            content=content,
            dependencies=dependencies,
            eval_spec=eval_spec,
            author_id=author_id,
            cost_profile=cost_profile_enum,
            cost_drivers=cost_drivers,
            estimated_duration=estimated_duration_val,
            extends=extends,
            changelog=data.changelog,
        )

        return updated

    async def get_skill(self, slug: str, version: str | None = None) -> Skill | None:
        """Return a skill by slug (and optional version)."""
        return await self._skill_repo.get_by_slug(slug, version=version)

    async def list_skills(
        self,
        category_id: uuid_mod.UUID | None = None,
        trust_tier: TrustTier | None = None,
    ) -> list[SkillSummary]:
        """Return skill summaries with optional filters."""
        return await self._skill_repo.list_all(category_id=category_id, trust_tier=trust_tier)
