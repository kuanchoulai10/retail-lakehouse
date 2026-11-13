"""Define the CompactionCandidateRowMapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.table_maintenance.application.port.outbound.compaction_candidate import (
    CandidateScore,
    CandidateState,
    CompactionCandidate,
    CompactionCandidateId,
    HoldReason,
    MaintenancePriority,
    PartitionKey,
    TableId,
    TableMaintenanceRunId,
)

if TYPE_CHECKING:
    from sqlalchemy import RowMapping


class CompactionCandidateRowMapper:
    """Map a CompactionCandidate to the columns of its row and back.

    The partition is stored in its canonical form (the unique key with the table);
    the spec id is repeated in its own column for queries. ``version`` is left
    to the repository, which owns the version check.
    """

    @staticmethod
    def to_values(candidate: CompactionCandidate) -> dict[str, Any]:
        """Return the column values of the candidate's row."""
        return {
            "id": candidate.id.value,
            "table_uuid": candidate.table_uuid.value,
            "partition_key": candidate.partition.canonical(),
            "spec_id": candidate.partition.spec_id,
            "label": candidate.label,
            "state": candidate.state.value,
            "hold_reason": None if candidate.hold_reason is None else candidate.hold_reason.value,
            "reducible_files": candidate.score.reducible_files,
            "data_bytes": candidate.score.data_bytes,
            "estimated_gb_hours": candidate.score.estimated_gb_hours,
            "score": candidate.score.score,
            "last_written_at": candidate.last_written_at,
            "waiting_since": candidate.waiting_since,
            "observed_at": candidate.observed_at,
            "claimed_by_run_id": None if candidate.claimed_by_run_id is None else candidate.claimed_by_run_id.value,
            "lease_expires_at": candidate.lease_expires_at,
            "updated_at": candidate.updated_at,
            "priority": candidate.priority.value,
            "granted_round_id": candidate.granted_round_id,
            "pending_since": candidate.pending_since,
        }

    @staticmethod
    def to_aggregate(row: RowMapping) -> CompactionCandidate:
        """Rebuild the candidate from its row.

        A ``not_due`` row stored while every not-due hold kept the wait (fix
        round 1 of milestone 4) still carries ``pending_since``; only a
        cooldown keeps it now, so that wait is read as ended.
        """
        hold_reason = None if row["hold_reason"] is None else HoldReason(row["hold_reason"])
        run_id = row["claimed_by_run_id"]
        pending_since = None if hold_reason is HoldReason.NOT_DUE else row["pending_since"]
        return CompactionCandidate(
            id=CompactionCandidateId(row["id"]),
            table_uuid=TableId(row["table_uuid"]),
            partition=PartitionKey.from_canonical(row["partition_key"]),
            label=row["label"],
            state=CandidateState(row["state"]),
            hold_reason=hold_reason,
            score=CandidateScore(
                reducible_files=row["reducible_files"],
                data_bytes=row["data_bytes"],
                estimated_gb_hours=float(row["estimated_gb_hours"]),
                score=float(row["score"]),
            ),
            last_written_at=row["last_written_at"],
            waiting_since=row["waiting_since"],
            observed_at=row["observed_at"],
            claimed_by_run_id=None if run_id is None else TableMaintenanceRunId(run_id),
            lease_expires_at=row["lease_expires_at"],
            updated_at=row["updated_at"],
            priority=MaintenancePriority(row["priority"]),
            granted_round_id=row["granted_round_id"],
            pending_since=pending_since,
            version=row["version"],
        )
