"""RegistryService: create, retrieve and list skills."""

import uuid as uuid_mod

from loom.db.repositories.category_repo import CategoryRepo
from loom.db.repositories.skill_repo import SkillRepo
from loom.models.skill import Skill, SkillCreate, SkillSummary
from loom.services.eval import EvalService


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
            estimated_duration=data.estimated_duration.value
            if hasattr(data.estimated_duration, "value")
            else data.estimated_duration,
            extends=data.extends,
            embedding=embedding,
        )

    async def get_skill(self, slug: str, version: str | None = None) -> Skill | None:
        """Return a skill by slug (and optional version)."""
        return await self._skill_repo.get_by_slug(slug, version=version)

    async def list_skills(
        self,
        category_id: uuid_mod.UUID | None = None,
        trust_tier: None = None,
    ) -> list[SkillSummary]:
        """Return skill summaries with optional filters."""
        return await self._skill_repo.list_all(category_id=category_id, trust_tier=trust_tier)
