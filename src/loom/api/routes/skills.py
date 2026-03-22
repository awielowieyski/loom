"""Skill API routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from loom.api.deps import get_discovery_service, get_registry_service
from loom.api.middleware import verify_api_key
from loom.models.common import CostProfile, TrustTier
from loom.models.resolution import ResolutionContext, ResolutionError, ResolvedSkill
from loom.models.skill import Skill, SkillSummary, SkillUpdate
from loom.services.discovery import DiscoveryService
from loom.services.registry import RegistryService

# M1: use a fixed system author ID for API-level operations
_SYSTEM_AUTHOR_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

router = APIRouter(prefix="/api/v1/skills", tags=["skills"])


class ResolveRequest(BaseModel):
    task_description: str
    context: dict[str, object] | None = None


@router.get("", response_model=list[SkillSummary])
async def list_skills(
    _: Annotated[str, Depends(verify_api_key)],
    registry: Annotated[RegistryService, Depends(get_registry_service)],
    trust_tier: Annotated[TrustTier | None, Query()] = None,
) -> list[SkillSummary]:
    """List skills with optional trust_tier filter."""
    return await registry.list_skills(trust_tier=trust_tier)


@router.get("/search", response_model=list[SkillSummary])
async def search_skills(
    _: Annotated[str, Depends(verify_api_key)],
    discovery: Annotated[DiscoveryService, Depends(get_discovery_service)],
    query: Annotated[str, Query()],
    trust_tier: Annotated[TrustTier | None, Query()] = None,
    cost_budget: Annotated[CostProfile | None, Query()] = None,
) -> list[SkillSummary]:
    """Search skills by natural-language query with optional filters."""
    return await discovery.search(
        query=query,
        trust_tier=trust_tier,
        cost_budget=cost_budget,
    )


@router.post("/resolve")
async def resolve_skill(
    body: ResolveRequest,
    _: Annotated[str, Depends(verify_api_key)],
    discovery: Annotated[DiscoveryService, Depends(get_discovery_service)],
) -> ResolvedSkill:
    """Resolve the best skill for a task description."""
    context: ResolutionContext | None = None
    if body.context is not None:
        context = ResolutionContext.model_validate(body.context)

    result = await discovery.resolve(body.task_description, context=context)

    if isinstance(result, ResolutionError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.model_dump(),
        )
    return result


@router.put("/{slug}", response_model=Skill)
async def update_skill(
    slug: str,
    body: SkillUpdate,
    _: Annotated[str, Depends(verify_api_key)],
    registry: Annotated[RegistryService, Depends(get_registry_service)],
) -> Skill:
    """Update a skill with a new version."""
    try:
        return await registry.update_skill(slug, body, author_id=_SYSTEM_AUTHOR_ID)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get("/{slug}", response_model=Skill)
async def get_skill(
    slug: str,
    _: Annotated[str, Depends(verify_api_key)],
    registry: Annotated[RegistryService, Depends(get_registry_service)],
    version: Annotated[str | None, Query()] = None,
) -> Skill:
    """Retrieve a skill by slug and optional version."""
    skill = await registry.get_skill(slug, version=version)
    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill {slug!r} not found",
        )
    return skill
