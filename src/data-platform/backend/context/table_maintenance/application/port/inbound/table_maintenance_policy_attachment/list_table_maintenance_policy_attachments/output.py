"""Define the ListTableMaintenancePolicyAttachmentsUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class ListTableMaintenancePolicyAttachmentsUseCaseOutputItem:
    """One attachment of the listing; ``orphaned`` when its target is no longer in the catalog."""

    type: str
    path: tuple[str, ...]
    table_uuid: str | None
    policy_name: str
    attached_at: datetime
    orphaned: bool


@dataclass(frozen=True)
class ListTableMaintenancePolicyAttachmentsUseCaseOutput:
    """Carry the listing."""

    items: list[ListTableMaintenancePolicyAttachmentsUseCaseOutputItem]
