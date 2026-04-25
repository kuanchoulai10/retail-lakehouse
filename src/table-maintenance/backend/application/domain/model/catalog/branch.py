"""Define the Branch entity."""

from __future__ import annotations

from dataclasses import dataclass

from core.base.entity import Entity
from application.domain.model.catalog.branch_id import BranchId
from application.domain.model.catalog.retention_policy import RetentionPolicy


@dataclass(eq=False)
class Branch(Entity[BranchId]):
    """A mutable branch ref pointing to a snapshot."""

    id: BranchId
    snapshot_id: int
    retention: RetentionPolicy | None = None
