"""Define the ListCompactionCandidatesUseCaseOutput."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from base import UseCaseOutput


class ListCompactionCandidatesUseCaseOutput(UseCaseOutput):
    """Carry a table's compaction candidates, best first, and how many one run takes."""

    class CompactionCandidate(UseCaseOutput):
        """One compaction candidate: its partition, score, priority, state and the round and run that hold it.

        ``spec_id`` -1 with no ``values`` stands for the whole table. ``rank`` is the
        candidate's place (1 is best) among the pending ones, None for the others.
        ``granted_round_id`` names the compaction round that granted it and
        ``granted_round_started_at`` when that round started (None once the round
        is no longer kept).
        ``pending_since`` is when it started to wait for a run (pending or granted
        ones only); ``overdue`` says it has waited longer than its priority's SLA.
        """

        spec_id: int
        values: tuple[Any, ...]
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
        granted_round_started_at: datetime | None = None

    partitions_per_run: int
    items: tuple[CompactionCandidate, ...]
