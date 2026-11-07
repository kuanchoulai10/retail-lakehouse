"""Define the catalog API DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StorageConfigApiRequest(BaseModel):
    """Carry the storage fields of the catalog forms; each type uses only its own fields."""

    model_config = ConfigDict(extra="forbid")

    storage_type: Literal["S3", "AZURE", "GCS", "FILE"]
    allowed_locations: list[str] = Field(default_factory=list)
    region: str | None = None
    role_arn: str | None = None
    external_id: str | None = None
    endpoint: str | None = None
    endpoint_internal: str | None = None
    sts_endpoint: str | None = None
    sts_unavailable: bool | None = None
    path_style_access: bool | None = None
    tenant_id: str | None = None
    multi_tenant_app_name: str | None = None
    consent_url: str | None = None
    gcs_service_account: str | None = None


class CreateCatalogApiRequest(BaseModel):
    """Carry the body that creates a catalog."""

    model_config = ConfigDict(extra="forbid")

    name: str
    type: Literal["INTERNAL", "EXTERNAL"]
    default_base_location: str
    storage_config: StorageConfigApiRequest


class UpdateCatalogApiRequest(BaseModel):
    """Carry the body that changes a catalog; ``entity_version`` is the version that was loaded."""

    model_config = ConfigDict(extra="forbid")

    entity_version: int
    default_base_location: str
    properties: dict[str, str] = Field(default_factory=dict)
    storage_config: StorageConfigApiRequest


class StorageConfigApiResponse(BaseModel):
    """Describe where a catalog keeps its data; unset fields are null."""

    model_config = ConfigDict(from_attributes=True)

    storage_type: str
    allowed_locations: list[str]
    region: str | None
    role_arn: str | None
    external_id: str | None
    user_arn: str | None
    endpoint: str | None
    endpoint_internal: str | None
    sts_endpoint: str | None
    sts_unavailable: bool | None
    path_style_access: bool | None
    tenant_id: str | None
    multi_tenant_app_name: str | None
    consent_url: str | None
    gcs_service_account: str | None


class CatalogApiResponse(BaseModel):
    """Describe a catalog."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    type: str
    default_base_location: str | None
    properties: dict[str, str]
    storage_config: StorageConfigApiResponse
    entity_version: int
    created_at: datetime | None
    updated_at: datetime | None
