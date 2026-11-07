"""Define POLARIS_STORAGE_FIELDS: the key of each StorageConfig field in Polaris's storageConfigInfo."""

from __future__ import annotations

POLARIS_STORAGE_FIELDS: dict[str, str] = {
    "storage_type": "storageType",
    "allowed_locations": "allowedLocations",
    "region": "region",
    "role_arn": "roleArn",
    "external_id": "externalId",
    "user_arn": "userArn",
    "endpoint": "endpoint",
    "endpoint_internal": "endpointInternal",
    "sts_endpoint": "stsEndpoint",
    "sts_unavailable": "stsUnavailable",
    "path_style_access": "pathStyleAccess",
    "tenant_id": "tenantId",
    "multi_tenant_app_name": "multiTenantAppName",
    "consent_url": "consentUrl",
    "gcs_service_account": "gcsServiceAccount",
}
