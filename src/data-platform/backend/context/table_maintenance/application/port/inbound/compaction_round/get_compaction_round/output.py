"""Define the GetCompactionRoundUseCaseOutput."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from base import UseCaseOutput


class GetCompactionRoundUseCaseOutput(UseCaseOutput):
    """One compaction round: when, its budget and what it used, its picks and the first of its skips."""

    class Pick(UseCaseOutput):
        """One partition a compaction round granted: its table, partition, priority and what it weighed.

        ``spec_id`` -1 with no ``values`` stands for the whole table. ``table_name``
        is the table's current name, None when the table is no longer known.
        """

        table_uuid: str
        table_name: str | None
        spec_id: int
        values: tuple[Any, ...]
        partition_label: str
        priority: str
        score: float
        weighted_score: float
        estimated_gb_hours: float
        overdue: bool
        catalog: str | None = None
        namespace: tuple[str, ...] | None = None
        table: str | None = None

    class Skip(UseCaseOutput):
        """One partition a compaction round left for later, what it weighed and why it was skipped."""

        table_uuid: str
        table_name: str | None
        spec_id: int
        values: tuple[Any, ...]
        partition_label: str
        priority: str
        score: float
        weighted_score: float
        estimated_gb_hours: float
        overdue: bool
        reason: str
        catalog: str | None = None
        namespace: tuple[str, ...] | None = None
        table: str | None = None

    round_id: str
    started_at: datetime
    budget_gb_hours: float
    used_gb_hours: float
    picks: tuple[Pick, ...]
    skips: tuple[Skip, ...]
    skipped_total: int
    busy_skipped: int = 0
