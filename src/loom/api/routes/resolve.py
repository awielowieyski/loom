"""Unified resolve API route — single entry point for skill or capability resolution."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from loom.api.deps import get_unified_resolver
from loom.api.middleware import verify_api_key
from loom.models.resolution import ResolutionContext, ResolutionError, ResolvedResult
from loom.services.unified_resolver import UnifiedResolver

router = APIRouter(prefix="/api/v1", tags=["resolve"])


class UnifiedResolveRequest(BaseModel):
    task_description: str
    context: ResolutionContext | None = None
    type: Literal["any", "skill", "capability"] = "any"


@router.post("/resolve", response_model=ResolvedResult)
async def unified_resolve(
    body: UnifiedResolveRequest,
    _: Annotated[str | None, Depends(verify_api_key)],
    resolver: Annotated[UnifiedResolver, Depends(get_unified_resolver)],
) -> ResolvedResult:
    """Resolve the best skill or capability for a task description."""
    result = await resolver.resolve(
        body.task_description,
        context=body.context,
        type_filter=body.type,
    )

    if isinstance(result, ResolutionError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.model_dump(),
        )
    return result
