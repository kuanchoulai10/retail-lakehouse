"""Define the ListCompactionRoundsUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from typing import Any


@dataclass(frozen=True)
class ListCompactionRoundsUseCaseOutputPick:
    """One partition a compaction round granted: its table, partition, priority and what it weighed.

    ``spec_id`` -1 with no ``values`` stands for the whole table. ``table_name``
    is the table's current name, None when the table is no longer known.
    """

    table_uuid: str
    table_name: str | None
    spec_id: int
    values: list[Any]
    partition_label: str
    priority: str
    score: float
    weighted_score: float
    estimated_gb_hours: float
    overdue: bool
    catalog: str | None = None
    namespace: list[str] | None = None
    table: str | None = None


@dataclass(frozen=True)
class ListCompactionRoundsUseCaseOutputSkip:
    """One partition a compaction round left for later, what it weighed and why it was skipped."""

    table_uuid: str
    table_name: str | None
    spec_id: int
    values: list[Any]
    partition_label: str
    priority: str
    score: float
    weighted_score: float
    estimated_gb_hours: float
    overdue: bool
    reason: str
    catalog: str | None = None
    namespace: list[str] | None = None
    table: str | None = None


@dataclass(frozen=True)
class ListCompactionRoundsUseCaseOutputItem:
    """One compaction round: when, its budget and what it used, its picks and the first of its skips."""

    round_id: str
    started_at: datetime
    budget_gb_hours: float
    used_gb_hours: float
    picks: list[ListCompactionRoundsUseCaseOutputPick]
    skips: list[ListCompactionRoundsUseCaseOutputSkip]
    skipped_total: int
    busy_skipped: int = 0


@dataclass(frozen=True)
class ListCompactionRoundsUseCaseOutput:
    """Carry the rounds, newest first."""

    items: list[ListCompactionRoundsUseCaseOutputItem]
