"""Define the ListCatalogsUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from typing import Any


@dataclass(frozen=True)
class ListCatalogsUseCaseOutputItem:
    """One catalog of the listing."""

    name: str
    type: str
    default_base_location: str | None
    properties: dict[str, str]
    storage_config: dict[str, Any]
    entity_version: int
    created_at: datetime | None
    updated_at: datetime | None


@dataclass(frozen=True)
class ListCatalogsUseCaseOutput:
    """Carry the listing."""

    items: list[ListCatalogsUseCaseOutputItem]
