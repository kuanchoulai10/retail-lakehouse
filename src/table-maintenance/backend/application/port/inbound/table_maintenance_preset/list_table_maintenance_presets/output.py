"""Define the ListTableMaintenancePresetsUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from typing import Any


@dataclass(frozen=True)
class ListTableMaintenancePresetsUseCaseOutputItem:
    """One entry of the listing."""

    id: str
    name: str
    settings: dict[str, Any]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ListTableMaintenancePresetsUseCaseOutput:
    """Carry the listing."""

    items: list[ListTableMaintenancePresetsUseCaseOutputItem]
