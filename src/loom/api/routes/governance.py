"""Governance API routes for review queue and decisions."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from loom.api.deps import get_governance_service
from loom.services.governance_service import GovernanceService

router = APIRouter(prefix="/api/v1/governance", tags=["governance"])


class ReviewSubmission(BaseModel):
    queue_item_id: str
    decision: str  # approve, reject, request_changes
    note: str


@router.get("/queue")
async def get_queue(
    service: Annotated[GovernanceService, Depends(get_governance_service)],
    reason: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[dict[str, Any]]:
    """Return governance review queue items."""
    return await service.get_queue(reason=reason, limit=limit, offset=offset)


@router.post("/review")
async def submit_review(
    body: ReviewSubmission,
    service: Annotated[GovernanceService, Depends(get_governance_service)],
) -> dict[str, Any]:
    """Submit a governance review decision."""
    return await service.submit_review(
        queue_item_id=body.queue_item_id,
        decision=body.decision,
        note=body.note,
    )
