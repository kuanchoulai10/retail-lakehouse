"""Define the GetTableHealthUseCaseOutput and its item."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class GetTableHealthUseCaseOutputItem:
    """Describe the scheduler's verdict on one maintenance operation."""

    operation: str
    verdict: str
    measured: int | None
    threshold: int | None
    next_eligible_at: datetime | None
    qualifying_partitions: int | None
    size_bytes: int | None
    size_source: str | None


@dataclass(frozen=True)
class GetTableHealthUseCaseOutput:
    """Describe the maintenance evaluation of a table and its delete files."""

    scheduled: bool
    not_scheduled_reason: str | None
    operations: list[GetTableHealthUseCaseOutputItem]
    position_delete_files: int
    equality_delete_files: int
