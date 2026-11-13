"""Define the compaction candidate API DTOs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CandidatePartitionApiResponse(BaseModel):
    """Name a candidate's partition by spec id and values; spec id -1 with no values is the whole table."""

    spec_id: int
    values: list[str | int | float | bool | None]


class CompactionCandidateApiResponse(BaseModel):
    """Describe one partition that needs compaction: what it is worth, its state and the run that holds it.

    ``rank`` is its place (1 is best) among the pending candidates, null for the others.
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


class CompactionCandidatesApiResponse(BaseModel):
    """List a table's compaction candidates, best first, and how many partitions one run compacts."""

    partitions_per_run: int
    candidates: list[CompactionCandidateApiResponse]
