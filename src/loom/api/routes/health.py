"""Health check endpoint."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health", response_class=JSONResponse)
async def health() -> dict[str, str]:
    """Return service health status."""
    return {"status": "ok"}
