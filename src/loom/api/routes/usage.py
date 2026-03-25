"""Usage reporting and statistics API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from loom.api.deps import get_skill_repo, get_usage_repo
from loom.api.middleware import verify_api_key
from loom.db.repositories.skill_repo import SkillRepo
from loom.db.repositories.usage_repo import UsageRepo
from loom.models.usage import UsageReport, UsageReportCreate, UsageStats
from loom.services.usage_service import UsageService

router = APIRouter(prefix="/api/v1", tags=["usage"])


def _make_usage_service(usage_repo: UsageRepo, skill_repo: SkillRepo) -> UsageService:
    return UsageService(usage_repo=usage_repo, skill_repo=skill_repo)


@router.post("/usage/report", status_code=201, response_model=UsageReport)
async def report_usage(
    report: UsageReportCreate,
    _: Annotated[str | None, Depends(verify_api_key)],
    usage_repo: Annotated[UsageRepo, Depends(get_usage_repo)],
    skill_repo: Annotated[SkillRepo, Depends(get_skill_repo)],
) -> UsageReport:
    """Report usage outcome. Idempotent on idempotency_key."""
    svc = _make_usage_service(usage_repo, skill_repo)
    try:
        return await svc.report_usage(report)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get("/skills/{slug}/usage", response_model=UsageStats)
async def get_usage_stats(
    slug: str,
    _: Annotated[str | None, Depends(verify_api_key)],
    usage_repo: Annotated[UsageRepo, Depends(get_usage_repo)],
    skill_repo: Annotated[SkillRepo, Depends(get_skill_repo)],
) -> UsageStats:
    """Return aggregate usage statistics for a skill."""
    svc = _make_usage_service(usage_repo, skill_repo)
    try:
        return await svc.get_usage_stats(slug)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
