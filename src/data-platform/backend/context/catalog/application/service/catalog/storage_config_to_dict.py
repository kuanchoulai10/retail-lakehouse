"""Define the storage_config_to_dict function."""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from context.catalog.application.domain.model.catalog import StorageConfig


def storage_config_to_dict(config: StorageConfig) -> dict[str, Any]:
    """Return every StorageConfig field by its snake_case name; unset ones are None."""
    return {**asdict(config), "allowed_locations": list(config.allowed_locations)}
