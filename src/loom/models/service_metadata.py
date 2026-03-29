"""External service and pricing evidence domain models."""

import uuid as uuid_mod
from datetime import datetime

from pydantic import BaseModel, Field


class ExternalService(BaseModel):
    id: uuid_mod.UUID
    service_key: str
    display_name: str
    vendor_name: str | None = None
    service_type: str = "other"
    homepage_url: str | None = None
    docs_url: str | None = None
    pricing_url: str | None = None
    default_auth_methods: list[str] = Field(default_factory=list)
    default_env_vars: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ServiceSetupRequirement(BaseModel):
    id: uuid_mod.UUID
    skill_version_id: uuid_mod.UUID
    service_id: uuid_mod.UUID
    requirement_type: str
    key: str | None = None
    value_hint: str | None = None
    required: bool = True
    instructions: str | None = None
    evidence_summary: dict[str, object] = Field(default_factory=dict)
    created_at: datetime | None = None


class PricingFact(BaseModel):
    id: uuid_mod.UUID
    subject_kind: str
    subject_id: uuid_mod.UUID
    fact_type: str
    pricing_model: str
    operation_name: str | None = None
    unit_name: str | None = None
    unit_cost_usd: float | None = None
    currency: str | None = None
    price_text_raw: str | None = None
    price_structured: dict[str, object] = Field(default_factory=dict)
    source_kind: str
    source_artifact_id: uuid_mod.UUID | None = None
    source_uri: str | None = None
    evidence_snippet: str | None = None
    confidence: float | None = None
    observed_at: datetime | None = None
    superseded_by: uuid_mod.UUID | None = None
    created_at: datetime | None = None


class SkillExternalService(BaseModel):
    id: uuid_mod.UUID
    skill_version_id: uuid_mod.UUID
    service_id: uuid_mod.UUID
    required: bool = True
    dependency_role: str
    operations: list[str] = Field(default_factory=list)
    pricing_summary: dict[str, object] = Field(default_factory=dict)
    evidence_summary: dict[str, object] = Field(default_factory=dict)
    created_at: datetime | None = None
    service: ExternalService


class ServiceDependencyWrite(BaseModel):
    service_key: str
    display_name: str
    vendor_name: str | None = None
    service_type: str = "other"
    homepage_url: str | None = None
    docs_url: str | None = None
    pricing_url: str | None = None
    default_auth_methods: list[str] = Field(default_factory=list)
    default_env_vars: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)
    required: bool = True
    dependency_role: str = "primary_runtime"
    operations: list[str] = Field(default_factory=list)
    pricing_summary: dict[str, object] = Field(default_factory=dict)
    evidence_summary: dict[str, object] = Field(default_factory=dict)


class ServiceSetupRequirementWrite(BaseModel):
    service_key: str
    requirement_type: str
    key: str | None = None
    value_hint: str | None = None
    required: bool = True
    instructions: str | None = None
    evidence_summary: dict[str, object] = Field(default_factory=dict)


class PricingFactWrite(BaseModel):
    fact_type: str
    pricing_model: str
    operation_name: str | None = None
    unit_name: str | None = None
    unit_cost_usd: float | None = None
    currency: str | None = None
    price_text_raw: str | None = None
    price_structured: dict[str, object] = Field(default_factory=dict)
    source_kind: str = "artifact"
    source_artifact_id: uuid_mod.UUID | None = None
    source_uri: str | None = None
    evidence_snippet: str | None = None
    confidence: float | None = None
    observed_at: datetime | None = None
