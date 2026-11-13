"""Define the ListCompactionCandidatesUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from typing import Any


@dataclass(frozen=True)
class ListCompactionCandidatesUseCaseOutputItem:
    """One compaction candidate: its partition, score, priority, state and the round and run that hold it.

    ``spec_id`` -1 with no ``values`` stands for the whole table. ``rank`` is the
    candidate's place (1 is best) among the pending ones, None for the others.
    ``granted_round_id`` names the compaction round that granted it.
    ``pending_since`` is when it started to wait for a run (pending or granted
    ones only); ``overdue`` says it has waited longer than its priority's SLA.
    """

    spec_id: int
    values: list[Any]
    partition_label: str
    state: str
    hold_reason: str | None
    reducible_files: int
    data_bytes: int
    estimated_gb_hours: float
    score: float
    rank: int | None
    claimed_by_run_id: str | None
    lease_expires_at: datetime | None
    last_written_at: datetime | None
    observed_at: datetime
    priority: str
    granted_round_id: str | None
    pending_since: datetime | None
    overdue: bool


@dataclass(frozen=True)
class ListCompactionCandidatesUseCaseOutput:
    """Carry a table's compaction candidates, best first, and how many one run takes."""

    partitions_per_run: int
    items: list[ListCompactionCandidatesUseCaseOutputItem]
