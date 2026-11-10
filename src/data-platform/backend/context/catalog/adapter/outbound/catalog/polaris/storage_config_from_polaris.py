"""Define the storage_config_from_polaris function."""

from __future__ import annotations

from typing import Any

from context.catalog.adapter.outbound.catalog.polaris.polaris_enum import polaris_enum
from context.catalog.adapter.outbound.catalog.polaris.polaris_storage_fields import (
    POLARIS_STORAGE_FIELDS,
)
from context.catalog.application.port.outbound.catalog import StorageConfig, StorageType


def storage_config_from_polaris(info: dict[str, Any]) -> StorageConfig:
    """Map Polaris's ``storageConfigInfo``; unknown keys are dropped, an unknown type raises ValueError.

    A missing or null ``allowedLocations`` is empty; one that is not a list raises TypeError.
    """
    values = {field: info[key] for field, key in POLARIS_STORAGE_FIELDS.items() if info.get(key) is not None}
    values["storage_type"] = polaris_enum(StorageType, info.get("storageType"), "storage type")
    locations = info.get("allowedLocations")
    if locations is not None and not isinstance(locations, list):
        raise TypeError(f"allowedLocations must be a list, not {locations!r}")
    values["allowed_locations"] = tuple(locations or ())
    return StorageConfig(**values)
