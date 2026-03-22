"""Category API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends

from loom.api.deps import get_category_repo
from loom.api.middleware import verify_api_key
from loom.db.repositories.category_repo import CategoryRepo
from loom.models.category import Category

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])


@router.get("", response_model=list[Category])
async def list_categories(
    _: Annotated[str, Depends(verify_api_key)],
    category_repo: Annotated[CategoryRepo, Depends(get_category_repo)],
) -> list[Category]:
    """List all categories."""
    return await category_repo.list_all()
