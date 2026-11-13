"""Web adapter for the compaction_round group."""

from __future__ import annotations

from context.table_maintenance.adapter.inbound.web.compaction_round.dto import (
    CompactionRoundApiResponse,
    CompactionRoundPartitionApiResponse,
    CompactionRoundPickApiResponse,
    CompactionRoundSkipApiResponse,
)
from context.table_maintenance.adapter.inbound.web.compaction_round.router import (
    router,
)

__all__ = [
    "CompactionRoundApiResponse",
    "CompactionRoundPartitionApiResponse",
    "CompactionRoundPickApiResponse",
    "CompactionRoundSkipApiResponse",
    "router",
]
