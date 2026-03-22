"""Category domain models."""

import uuid as uuid_mod
from datetime import datetime

from pydantic import BaseModel


class Category(BaseModel):
    id: uuid_mod.UUID
    slug: str
    name: str
    description: str | None = None
    parent_id: uuid_mod.UUID | None = None
    created_at: datetime | None = None


class CategoryCreate(BaseModel):
    slug: str
    name: str
    description: str | None = None
    parent_id: uuid_mod.UUID | None = None
