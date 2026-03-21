"""User domain models."""

import uuid as uuid_mod
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class User(BaseModel):
    id: uuid_mod.UUID
    handle: str
    email: str
    role: Literal["contributor", "steward", "maintainer"] = "contributor"
    signing_public_key: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UserCreate(BaseModel):
    handle: str
    email: str
    role: Literal["contributor", "steward", "maintainer"] = "contributor"
