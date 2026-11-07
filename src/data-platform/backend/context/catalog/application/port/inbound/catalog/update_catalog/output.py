"""Define the UpdateCatalogUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from typing import Any


@dataclass(frozen=True)
class UpdateCatalogUseCaseOutput:
    """Describe the catalog."""

    name: str
    type: str
    default_base_location: str | None
    properties: dict[str, str]
    storage_config: dict[str, Any]
    connection_config: dict[str, Any] | None
    entity_version: int
    created_at: datetime | None
    updated_at: datetime | None
