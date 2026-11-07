"""Define the storage_config_from_dict function."""

from __future__ import annotations

from dataclasses import fields
from typing import Any

from context.catalog.application.domain.model.catalog import StorageConfig, StorageType
from context.catalog.application.exceptions import ValidationError

_ASSIGNED_BY_THE_CATALOG = frozenset({"user_arn"})
_FIELDS = frozenset(f.name for f in fields(StorageConfig)) - _ASSIGNED_BY_THE_CATALOG
_STORAGE_TYPES = ", ".join(StorageType)


def storage_config_from_dict(data: dict[str, Any]) -> StorageConfig:
    """Build a StorageConfig from its snake_case input fields.

    Unknown fields are rejected, and so is ``user_arn``, which the catalog service assigns.
    ``storage_type`` is required, and AZURE storage also needs ``tenant_id``.
    """
    unknown = sorted(set(data) - _FIELDS)
    if unknown:
        raise ValidationError(f"unknown storage config field(s): {', '.join(unknown)}")
    raw_type = data.get("storage_type")
    if not isinstance(raw_type, str) or not raw_type.strip():
        raise ValidationError("storage_config.storage_type is required")
    try:
        storage_type = StorageType(raw_type)
    except ValueError:
        raise ValidationError(f"storage type must be one of {_STORAGE_TYPES}, not {raw_type!r}") from None
    if storage_type is StorageType.AZURE and not data.get("tenant_id"):
        raise ValidationError("storage_config.tenant_id is required for AZURE storage")
    values: dict[str, Any] = {
        **data,
        "storage_type": storage_type,
        "allowed_locations": tuple(data.get("allowed_locations") or ()),
    }
    return StorageConfig(**values)
