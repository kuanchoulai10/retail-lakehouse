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


class AuthenticationParametersApiRequest(BaseModel):
    """Carry how an external catalog's connection authenticates; each field belongs to one type.

    OAUTH uses ``token_uri``, ``client_id``, ``client_secret`` and ``scopes``; BEARER uses
    ``bearer_token``; SIGV4 uses the ``role_*``, ``external_id`` and ``signing_*`` fields;
    IMPLICIT uses none. The secrets are sent to the catalog and never returned.
    """

    model_config = ConfigDict(extra="forbid")

    authentication_type: Literal["OAUTH", "BEARER", "SIGV4", "IMPLICIT"] | None = None
    token_uri: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    scopes: list[str] | None = None
    bearer_token: str | None = None
    role_arn: str | None = None
    role_session_name: str | None = None
    external_id: str | None = None
    signing_region: str | None = None
    signing_name: str | None = None


class ConnectionConfigApiRequest(BaseModel):
    """Carry the remote catalog service an EXTERNAL catalog connects to.

    ``connection_type`` REST is a catalog that speaks the Iceberg REST protocol.
    """

    model_config = ConfigDict(extra="forbid")

    connection_type: Literal["REST", "HADOOP", "HIVE"] | None = None
    uri: str | None = None
    authentication: AuthenticationParametersApiRequest | None = None


class CreateCatalogApiRequest(BaseModel):
    """Carry the body that creates a catalog; an EXTERNAL catalog also needs ``connection_config``."""

    model_config = ConfigDict(extra="forbid")

    name: str
    type: Literal["INTERNAL", "EXTERNAL"]
    default_base_location: str
    storage_config: StorageConfigApiRequest
    connection_config: ConnectionConfigApiRequest | None = None


class UpdateCatalogApiRequest(BaseModel):
    """Carry the body that changes a catalog.

    ``entity_version`` is the version that was loaded. ``properties`` replace the current ones,
    so they are required: a body that leaves them out must not wipe them.
    """

    model_config = ConfigDict(extra="forbid")

    entity_version: int
    default_base_location: str
    properties: dict[str, str]
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


class AuthenticationParametersApiResponse(BaseModel):
    """Describe how a connection authenticates; secrets are never part of it."""

    model_config = ConfigDict(from_attributes=True)

    authentication_type: str
    token_uri: str | None
    client_id: str | None
    scopes: list[str]
    role_arn: str | None
    role_session_name: str | None
    external_id: str | None
    signing_region: str | None
    signing_name: str | None


class ConnectionConfigApiResponse(BaseModel):
    """Describe the remote catalog service an EXTERNAL catalog connects to."""

    model_config = ConfigDict(from_attributes=True)

    connection_type: str
    uri: str | None
    authentication: AuthenticationParametersApiResponse | None


class CatalogApiResponse(BaseModel):
    """Describe a catalog."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    type: str
    default_base_location: str | None
    properties: dict[str, str]
    storage_config: StorageConfigApiResponse
    connection_config: ConnectionConfigApiResponse | None
    entity_version: int
    created_at: datetime | None
    updated_at: datetime | None
