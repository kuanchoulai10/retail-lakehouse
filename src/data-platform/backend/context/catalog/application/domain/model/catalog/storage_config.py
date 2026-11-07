"""Define the StorageConfig value object."""

from __future__ import annotations

from dataclasses import dataclass

from base import ValueObject


@dataclass(frozen=True)
class StorageConfig(ValueObject):
    """Where a catalog may keep its data and how to reach that storage.

    ``storage_type`` is ``S3``, ``AZURE``, ``GCS`` or ``FILE``; ``allowed_locations`` are the
    location prefixes tables may use. The other fields apply to one storage type each and
    are ``None`` when unset: the S3 ones (``region`` to ``path_style_access``), the Azure
    ones (``tenant_id``, ``multi_tenant_app_name``, ``consent_url``) and the GCS one
    (``gcs_service_account``). ``user_arn`` is assigned by the catalog service, never sent.
    """

    storage_type: str
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
    tenant_id: str | None = None
    multi_tenant_app_name: str | None = None
    consent_url: str | None = None
    gcs_service_account: str | None = None
