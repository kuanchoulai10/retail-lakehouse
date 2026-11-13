"""Define the CompactionCandidateId identifier."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from base import EntityId

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.compaction_candidate.partition_key import (
        PartitionKey,
    )
    from context.table_maintenance.application.domain.model.table import TableId


class CompactionCandidateId(EntityId):
    """Identify a CompactionCandidate; one per table and partition."""

    @classmethod
    def for_partition(cls, table_uuid: TableId, partition: PartitionKey) -> CompactionCandidateId:
        """Return the id of the candidate of ``partition`` of ``table_uuid``, the same on every observation."""
        digest = hashlib.sha256(f"{table_uuid.value}\x1f{partition.canonical()}".encode()).hexdigest()
        return cls(digest[:32])
