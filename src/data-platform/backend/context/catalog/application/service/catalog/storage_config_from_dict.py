"""Define the storage_config_from_dict function."""

from __future__ import annotations

from dataclasses import fields
from typing import Any

from context.catalog.application.domain.model.catalog import StorageConfig
from context.catalog.application.exceptions import ValidationError

_FIELDS = frozenset(f.name for f in fields(StorageConfig))


def storage_config_from_dict(data: dict[str, Any]) -> StorageConfig:
    """Build a StorageConfig from its snake_case fields, rejecting unknown fields and a missing type."""
    unknown = sorted(set(data) - _FIELDS)
    if unknown:
        raise ValidationError(f"unknown storage config field(s): {', '.join(unknown)}")
    storage_type = data.get("storage_type")
    if not isinstance(storage_type, str) or not storage_type.strip():
        raise ValidationError("storage_config.storage_type is required")
    values: dict[str, Any] = {**data, "allowed_locations": tuple(data.get("allowed_locations") or ())}
    return StorageConfig(**values)
