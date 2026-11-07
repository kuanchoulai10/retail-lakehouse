"""Define the catalog_output_fields function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.catalog.application.service.catalog.storage_config_to_dict import (
    storage_config_to_dict,
)

if TYPE_CHECKING:
    from context.catalog.application.domain.model.catalog import Catalog


def catalog_output_fields(catalog: Catalog) -> dict[str, Any]:
    """Return the primitive fields shared by every catalog output."""
    return {
        "name": catalog.name,
        "type": catalog.type.value,
        "default_base_location": catalog.default_base_location,
        "properties": dict(catalog.properties),
        "storage_config": storage_config_to_dict(catalog.storage_config),
        "entity_version": catalog.entity_version,
        "created_at": catalog.created_at,
        "updated_at": catalog.updated_at,
    }
