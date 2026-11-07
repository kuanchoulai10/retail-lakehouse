"""Define the UpdateCatalogUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class UpdateCatalogUseCaseInput:
    """Carry the edit catalog form.

    ``entity_version`` is the version the caller loaded; the update is refused when the
    catalog changed since. ``properties`` replace the current ones, and
    ``default_base_location`` sets the ``default-base-location`` property.
    """

    name: str
    entity_version: int
    default_base_location: str
    storage_config: dict[str, Any]
    properties: dict[str, str] = field(default_factory=dict)
