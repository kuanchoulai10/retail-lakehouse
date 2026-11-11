"""Define the ListTableMaintenancePoliciesUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from typing import Any


@dataclass(frozen=True)
class ListTableMaintenancePoliciesUseCaseOutputItem:
    """One entry of the listing."""

    name: str
    content: dict[str, Any]
    version: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ListTableMaintenancePoliciesUseCaseOutput:
    """Carry the listing."""

    items: list[ListTableMaintenancePoliciesUseCaseOutputItem]
