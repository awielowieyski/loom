"""M4 skill routes: behavioral results, deprecation, comparison."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from loom.api.deps import (
    get_behavioral_eval_repo,
    get_skill_repo,
    get_usage_repo,
)
from loom.api.middleware import verify_api_key
from loom.db.repositories.behavioral_eval_repo import BehavioralEvalRepo
from loom.db.repositories.skill_repo import SkillRepo
from loom.db.repositories.usage_repo import UsageRepo
from loom.models.behavioral import BehavioralRunResult
from loom.services.usage_service import UsageService

router = APIRouter(prefix="/api/v1", tags=["skills-m4"])


class DeprecateRequest(BaseModel):
    successor_slug: str | None = None


class CompareRequest(BaseModel):
    against_slug: str


@router.get("/skills/{slug}/behavioral", response_model=list[BehavioralRunResult])
async def get_behavioral_results(
    slug: str,
    _: Annotated[str, Depends(verify_api_key)],
    skill_repo: Annotated[SkillRepo, Depends(get_skill_repo)],
    behavioral_repo: Annotated[BehavioralEvalRepo, Depends(get_behavioral_eval_repo)],
) -> list[BehavioralRunResult]:
    """Return latest behavioral evaluation runs for a skill."""
    skill = await skill_repo.get_by_slug(slug)
    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill {slug!r} not found",
        )
    runs = await behavioral_repo.get_latest_behavioral_for_skill(skill.id)
    return runs or []


@router.post("/skills/{slug}/deprecate")
async def deprecate_skill(
    slug: str,
    body: DeprecateRequest,
    _: Annotated[str, Depends(verify_api_key)],
    usage_repo: Annotated[UsageRepo, Depends(get_usage_repo)],
    skill_repo: Annotated[SkillRepo, Depends(get_skill_repo)],
) -> dict[str, Any]:
    """Deprecate a skill with optional successor pointer."""
    svc = UsageService(usage_repo=usage_repo, skill_repo=skill_repo)
    try:
        return await svc.deprecate_skill(slug, successor_slug=body.successor_slug)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post("/skills/{slug}/compare", status_code=202)
async def compare_skills(
    slug: str,
    body: CompareRequest,
    _: Annotated[str, Depends(verify_api_key)],
    skill_repo: Annotated[SkillRepo, Depends(get_skill_repo)],
) -> dict[str, Any]:
    """Trigger head-to-head comparison. Returns 202 with job info (async)."""
    skill_a = await skill_repo.get_by_slug(slug)
    if skill_a is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill {slug!r} not found",
        )
    skill_b = await skill_repo.get_by_slug(body.against_slug)
    if skill_b is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill {body.against_slug!r} not found",
        )
    # In production this would enqueue an arq job; for now return accepted status
    return {
        "status": "accepted",
        "message": f"Comparison of {slug!r} vs {body.against_slug!r} queued",
        "skill_a": slug,
        "skill_b": body.against_slug,
    }
