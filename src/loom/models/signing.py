"""Domain models for ed25519 signing and key management."""

import uuid as uuid_mod
from datetime import datetime

from pydantic import BaseModel


class SigningKey(BaseModel):
    """Database record for a registered ed25519 public key."""

    id: uuid_mod.UUID
    user_id: uuid_mod.UUID
    fingerprint: str
    label: str | None = None
    revoked_at: datetime | None = None
    created_at: datetime | None = None


class SigningKeyCreate(BaseModel):
    """Input model for registering a new signing key."""

    public_key_base64: str
    label: str | None = None


class SignatureStatus(BaseModel):
    """Result of verifying a skill's signature."""

    signed: bool
    valid: bool = False
    fingerprint: str | None = None
    signer_handle: str | None = None
    revoked: bool = False
