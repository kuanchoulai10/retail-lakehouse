"""Define the compaction candidate API DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

type CandidatePriorityApi = Literal["P0", "P1", "P2"]


class CandidatePartitionApiResponse(BaseModel):
    """Name a candidate's partition by spec id and values; spec id -1 with no values is the whole table."""

    spec_id: int
    values: list[str | int | float | bool | None]


class CompactionCandidateApiResponse(BaseModel):
    """Describe one partition that needs compaction: what it is worth, its state and who holds it.

    ``rank`` is its place (1 is best) among the pending candidates, null for the
    others. ``granted_round_id`` names the compaction round that granted it and
    ``granted_round_started_at`` when it started (the round's name in the
    rounds list; null once the round is no longer kept);
    ``pending_since`` is when it started to wait for a run, and ``overdue`` says
    it has waited longer than its priority's SLA.
    """

    partition: CandidatePartitionApiResponse
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
    priority: CandidatePriorityApi
    granted_round_id: str | None
    pending_since: datetime | None
    overdue: bool
    granted_round_started_at: datetime | None


class CompactionCandidatesApiResponse(BaseModel):
    """List a table's compaction candidates, best first, and how many partitions one run compacts."""

    partitions_per_run: int
    candidates: list[CompactionCandidateApiResponse]
