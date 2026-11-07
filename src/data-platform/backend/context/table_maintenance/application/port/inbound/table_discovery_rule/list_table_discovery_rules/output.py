"""Define the ListTableDiscoveryRulesUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class ListTableDiscoveryRulesUseCaseOutputItem:
    """One entry of the listing."""

    id: str
    priority: int
    effect: str
    catalog_pattern: str
    namespace_pattern: str
    table_pattern: str
    preset_id: str | None
    enabled: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ListTableDiscoveryRulesUseCaseOutput:
    """Carry the listing."""

    items: list[ListTableDiscoveryRulesUseCaseOutputItem]
