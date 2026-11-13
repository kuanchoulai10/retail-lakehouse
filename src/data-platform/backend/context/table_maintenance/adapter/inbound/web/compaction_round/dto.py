"""Define the compaction round API DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

type RoundPriorityApi = Literal["P0", "P1", "P2"]
type RoundSkipReasonApi = Literal["budget_used", "table_share_used", "table_busy"]


class CompactionRoundPartitionApiResponse(BaseModel):
    """Name a partition by spec id and values; spec id -1 with no values is the whole table."""

    spec_id: int
    values: list[str | int | float | bool | None]


class CompactionRoundPickApiResponse(BaseModel):
    """Describe one partition a compaction round granted to its table, and what it weighed.

    ``weighted_score`` is ``score`` times the weight of ``priority``, the key the
    round ranked by. ``table_name`` is the table's current name, null when the
    table is no longer known.
    """

    table_uuid: str
    table_name: str | None
    partition: CompactionRoundPartitionApiResponse
    partition_label: str
    priority: RoundPriorityApi
    score: float
    weighted_score: float
    estimated_gb_hours: float
    overdue: bool


class CompactionRoundSkipApiResponse(BaseModel):
    """Describe one partition a compaction round left for a later round, and why."""

    table_uuid: str
    table_name: str | None
    partition: CompactionRoundPartitionApiResponse
    partition_label: str
    priority: RoundPriorityApi
    score: float
    weighted_score: float
    estimated_gb_hours: float
    overdue: bool
    reason: RoundSkipReasonApi


class CompactionRoundApiResponse(BaseModel):
    """Describe one compaction round: when it ran, its budget and use, its picks and the first of its skips.

    ``skips`` keeps the first skipped candidates; ``skipped_total`` counts them all.
    """

    round_id: str
    started_at: datetime
    budget_gb_hours: float
    used_gb_hours: float
    picks: list[CompactionRoundPickApiResponse]
    skips: list[CompactionRoundSkipApiResponse]
    skipped_total: int
