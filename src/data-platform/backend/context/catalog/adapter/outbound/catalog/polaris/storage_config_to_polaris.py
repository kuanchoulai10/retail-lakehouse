"""Define the storage_config_to_polaris function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.catalog.adapter.outbound.catalog.polaris.polaris_storage_fields import (
    POLARIS_STORAGE_FIELDS,
)

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.catalog import StorageConfig

_ASSIGNED_BY_POLARIS = frozenset({"user_arn"})


def storage_config_to_polaris(config: StorageConfig) -> dict[str, Any]:
    """Return Polaris's ``storageConfigInfo``: only the fields that are set, never ``userArn``."""
    info: dict[str, Any] = {}
    for field, key in POLARIS_STORAGE_FIELDS.items():
        value = getattr(config, field)
        if field in _ASSIGNED_BY_POLARIS or value is None or value == ():
            continue
        info[key] = list(value) if isinstance(value, tuple) else value
    return info
