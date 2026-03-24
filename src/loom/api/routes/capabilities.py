"""Capability API routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from loom.api.deps import (
    get_capability_discovery_service,
    get_capability_registry_service,
)
from loom.api.middleware import verify_api_key
from loom.models.capability import Capability, CapabilityCreate, CapabilitySummary, CapabilityUpdate
from loom.models.common import CostProfile, TrustTier
from loom.models.resolution import ResolutionContext, ResolutionError, ResolvedCapability
from loom.services.capability_discovery import CapabilityDiscoveryService
from loom.services.capability_registry import CapabilityRegistryService

# M3: use a fixed system author ID for API-level operations
_SYSTEM_AUTHOR_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

router = APIRouter(prefix="/api/v1/capabilities", tags=["capabilities"])


class ResolveCapabilityRequest(BaseModel):
    task_description: str
    context: dict[str, object] | None = None


@router.post("", response_model=Capability, status_code=status.HTTP_201_CREATED)
async def create_capability(
    body: CapabilityCreate,
    _: Annotated[str, Depends(verify_api_key)],
    registry: Annotated[CapabilityRegistryService, Depends(get_capability_registry_service)],
) -> Capability:
    """Create a new capability."""
    try:
        return await registry.create_capability(body, author_id=_SYSTEM_AUTHOR_ID)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get("", response_model=list[CapabilitySummary])
async def list_capabilities(
    _: Annotated[str, Depends(verify_api_key)],
    registry: Annotated[CapabilityRegistryService, Depends(get_capability_registry_service)],
    trust_tier: Annotated[TrustTier | None, Query()] = None,
) -> list[CapabilitySummary]:
    """List capabilities with optional trust_tier filter."""
    return await registry.list_capabilities(trust_tier=trust_tier)


@router.get("/search", response_model=list[CapabilitySummary])
async def search_capabilities(
    _: Annotated[str, Depends(verify_api_key)],
    discovery: Annotated[CapabilityDiscoveryService, Depends(get_capability_discovery_service)],
    query: Annotated[str, Query()],
    trust_tier: Annotated[TrustTier | None, Query()] = None,
    cost_budget: Annotated[CostProfile | None, Query()] = None,
) -> list[CapabilitySummary]:
    """Search capabilities by natural-language query with optional filters."""
    return await discovery.search(
        query=query,
        trust_tier=trust_tier,
        cost_budget=cost_budget,
    )


@router.post("/resolve", response_model=ResolvedCapability)
async def resolve_capability(
    body: ResolveCapabilityRequest,
    _: Annotated[str, Depends(verify_api_key)],
    discovery: Annotated[CapabilityDiscoveryService, Depends(get_capability_discovery_service)],
) -> ResolvedCapability:
    """Resolve the best capability for a task description."""
    try:
        context: ResolutionContext | None = None
        if body.context is not None:
            context = ResolutionContext.model_validate(body.context)

        result = await discovery.resolve(body.task_description, context=context)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    if isinstance(result, ResolutionError):
        detail = result.model_dump()
        if result.error == "step_resolution_failed":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=detail,
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )
    return result


@router.put("/{slug}", response_model=Capability)
async def update_capability(
    slug: str,
    body: CapabilityUpdate,
    _: Annotated[str, Depends(verify_api_key)],
    registry: Annotated[CapabilityRegistryService, Depends(get_capability_registry_service)],
) -> Capability:
    """Update a capability with a new version."""
    try:
        return await registry.update_capability(slug, body, author_id=_SYSTEM_AUTHOR_ID)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get("/{slug}", response_model=Capability)
async def get_capability(
    slug: str,
    _: Annotated[str, Depends(verify_api_key)],
    registry: Annotated[CapabilityRegistryService, Depends(get_capability_registry_service)],
    version: Annotated[str | None, Query()] = None,
) -> Capability:
    """Retrieve a capability by slug and optional version."""
    capability = await registry.get_capability(slug, version=version)
    if capability is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Capability {slug!r} not found",
        )
    return capability
