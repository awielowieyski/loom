"""API middleware and shared dependencies."""

from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    request: Request,
    api_key: str | None = Security(_api_key_header),
) -> str | None:
    """Verify API key for mutating requests; skip for read-only (GET/HEAD/OPTIONS).

    Proper auth (per-user tokens, RBAC) is planned for M6.
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return api_key  # allow anonymous reads
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or empty API key",
        )
    return api_key
