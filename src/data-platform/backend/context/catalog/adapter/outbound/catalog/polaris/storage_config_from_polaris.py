"""Define the storage_config_from_polaris function."""

from __future__ import annotations

from typing import Any

from context.catalog.adapter.outbound.catalog.polaris.polaris_storage_fields import (
    POLARIS_STORAGE_FIELDS,
)
from context.catalog.application.port.outbound.catalog import StorageConfig


def storage_config_from_polaris(info: dict[str, Any]) -> StorageConfig:
    """Map Polaris's ``storageConfigInfo``; keys this model does not know are dropped."""
    values = {field: info[key] for field, key in POLARIS_STORAGE_FIELDS.items() if info.get(key) is not None}
    values["storage_type"] = info.get("storageType", "")
    values["allowed_locations"] = tuple(info.get("allowedLocations") or ())
    return StorageConfig(**values)
