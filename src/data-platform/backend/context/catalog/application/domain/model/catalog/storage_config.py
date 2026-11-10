"""Define the StorageConfig value object."""

from __future__ import annotations

from pydantic import Field, ValidationInfo, field_validator

from base import ValueObject
from context.catalog.application.domain.model.catalog.storage_type import StorageType


class StorageConfig(ValueObject):
    """Where a catalog may keep its data and how to reach that storage.

    ``allowed_locations`` are the
    location prefixes tables may use. The other fields apply to one storage type each and
    are ``None`` when unset: the S3 ones (``region`` to ``path_style_access``), the Azure
    ones (``tenant_id``, ``multi_tenant_app_name``, ``consent_url``) and the GCS one
    (``gcs_service_account``). AZURE storage needs a ``tenant_id``. ``user_arn`` is assigned
    by the catalog service, never sent.
    """

    storage_type: StorageType
    allowed_locations: tuple[str, ...] = ()
    region: str | None = None
    role_arn: str | None = None
    external_id: str | None = None
    user_arn: str | None = None
    endpoint: str | None = None
    endpoint_internal: str | None = None
    sts_endpoint: str | None = None
    sts_unavailable: bool | None = None
    path_style_access: bool | None = None
    tenant_id: str | None = Field(default=None, validate_default=True)
    multi_tenant_app_name: str | None = None
    consent_url: str | None = None
    gcs_service_account: str | None = None

    @field_validator("tenant_id")
    @classmethod
    def _azure_needs_a_tenant(cls, value: str | None, info: ValidationInfo) -> str | None:
        if info.data.get("storage_type") is StorageType.AZURE and not value:
            raise ValueError("required for AZURE storage")
        return value
