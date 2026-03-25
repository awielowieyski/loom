"""Evaluation pipeline API routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from loom.api.deps import get_eval_repo, get_skill_repo
from loom.api.middleware import verify_api_key
from loom.db.repositories.eval_repo import EvalRepo
from loom.db.repositories.skill_repo import SkillRepo
from loom.models.eval import EvalJob, TrustAuditEntry

router = APIRouter(prefix="/api/v1", tags=["eval"])


@router.get("/skills/{skill_id}/eval", response_model=EvalJob | None)
async def get_latest_eval(
    skill_id: uuid.UUID,
    _: Annotated[str | None, Depends(verify_api_key)],
    eval_repo: Annotated[EvalRepo, Depends(get_eval_repo)],
) -> EvalJob | None:
    """Return the latest evaluation result for a skill."""
    return await eval_repo.get_latest_eval_for_skill(skill_id)


@router.get("/eval/jobs/{job_id}", response_model=EvalJob)
async def get_eval_job(
    job_id: uuid.UUID,
    _: Annotated[str | None, Depends(verify_api_key)],
    eval_repo: Annotated[EvalRepo, Depends(get_eval_repo)],
) -> EvalJob:
    """Return an evaluation job by ID."""
    job = await eval_repo.get_eval_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Eval job {job_id!s} not found",
        )
    return job


@router.get("/skills/{skill_id}/trust", response_model=list[TrustAuditEntry])
async def get_trust_history(
    skill_id: uuid.UUID,
    _: Annotated[str | None, Depends(verify_api_key)],
    eval_repo: Annotated[EvalRepo, Depends(get_eval_repo)],
) -> list[TrustAuditEntry]:
    """Return trust tier change history for a skill."""
    return await eval_repo.get_trust_history(skill_id)


@router.post("/skills/{skill_id}/eval/trigger", status_code=202)
async def trigger_evaluation(
    skill_id: uuid.UUID,
    request: Request,
    _: Annotated[str | None, Depends(verify_api_key)],
    skill_repo: Annotated[SkillRepo, Depends(get_skill_repo)],
) -> dict[str, str | None]:
    """Enqueue an evaluation job for a skill via the arq worker."""
    skill = await skill_repo.get_by_id(skill_id)
    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill {skill_id!s} not found",
        )

    arq_pool = getattr(request.app.state, "arq_pool", None)
    if arq_pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Background job queue not available",
        )

    job = await arq_pool.enqueue_job("run_eval_job", str(skill_id), "api")
    return {
        "status": "queued",
        "skill_id": str(skill_id),
        "arq_job_id": job.job_id if job else None,
    }
