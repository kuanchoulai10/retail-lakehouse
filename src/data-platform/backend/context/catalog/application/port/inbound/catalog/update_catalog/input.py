"""Define the UpdateCatalogUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class UpdateCatalogUseCaseInput:
    """Carry the edit catalog form.

    ``entity_version`` is the version the caller loaded; the update is refused when the
    catalog changed since. ``properties`` replace the current ones, so they are required:
    leaving them out must not wipe them. ``default_base_location`` sets the
    ``default-base-location`` property.
    """

    name: str
    entity_version: int
    default_base_location: str
    properties: dict[str, str]
    storage_config: dict[str, Any]
