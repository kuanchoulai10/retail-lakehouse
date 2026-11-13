"""Define the CompactionCandidate aggregate root."""

from __future__ import annotations

from datetime import datetime

from pydantic import model_validator

from base import AggregateRoot
from context.table_maintenance.application.domain.model.compaction_candidate.candidate_score import (
    CandidateScore,
)
from context.table_maintenance.application.domain.model.compaction_candidate.candidate_state import (
    CandidateState,
)
from context.table_maintenance.application.domain.model.compaction_candidate.compaction_candidate_id import (
    CompactionCandidateId,
)
from context.table_maintenance.application.domain.model.compaction_candidate.hold_reason import (
    HoldReason,
)
from context.table_maintenance.application.domain.model.compaction_candidate.invalid_candidate_transition import (
    InvalidCandidateTransition,
)
from context.table_maintenance.application.domain.model.compaction_candidate.partition_key import (
    PartitionKey,
)
from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    TableMaintenanceRunId,
)


class CompactionCandidate(AggregateRoot[CompactionCandidateId]):
    """Hold one partition of a table that needs compaction, how much it is worth and who works on it.

    One candidate exists per table and partition (``PartitionKey.whole_table()``
    for a compaction of the whole table). Observation creates and re-scores it;
    a reconcile claims the best pending ones for a run under a lease; the run
    starts them and finishes them; the next observation decides whether the
    partition is healthy (it leaves the candidates) or still needs work (it is
    pending again), whatever the run reported. A claim whose lease expired is
    given up by the next observation.

    ``label`` names the partition for people (``field=value`` pairs).
    ``waiting_since`` is when the candidate started to wait for writes to its
    partition to stop; it is kept while writes go on and cleared once they
    stop or the candidate is claimed, so a partition written without pause is
    not held forever. ``claimed_by_run_id`` names the run that holds the
    candidate (claimed, running) or last held it (done, failed).
    """

    id: CompactionCandidateId
    table_uuid: TableId
    partition: PartitionKey
    label: str
    state: CandidateState
    hold_reason: HoldReason | None = None
    score: CandidateScore
    last_written_at: datetime | None = None
    waiting_since: datetime | None = None
    observed_at: datetime
    claimed_by_run_id: TableMaintenanceRunId | None = None
    lease_expires_at: datetime | None = None
    updated_at: datetime

    @model_validator(mode="after")
    def _state_agrees_with_hold_claim_and_lease(self) -> CompactionCandidate:
        """Reject a hold reason, claim or lease the state does not allow."""
        if (self.state is CandidateState.HELD) != (self.hold_reason is not None):
            raise ValueError("a held candidate needs a hold reason, and only a held one has one")
        has_run = self.state.holds_a_claim or self.state.finished
        if has_run != (self.claimed_by_run_id is not None):
            raise ValueError(f"a {self.state.value} candidate {'needs' if has_run else 'has no'} run")
        if self.state.holds_a_claim != (self.lease_expires_at is not None):
            raise ValueError("a claimed or running candidate needs a lease, and only such a candidate has one")
        return self

    @property
    def rank(self) -> tuple[float, int, str]:
        """Sort key that puts the best candidate first.

        Best means the highest score; ties go to more removable files, then to the
        partition's canonical key, so the same candidates always sort the same way.
        """
        return (-self.score.score, -self.score.reducible_files, self.partition.canonical())

    @classmethod
    def create(  # noqa: PLR0913
        cls,
        *,
        table_uuid: TableId,
        partition: PartitionKey,
        label: str,
        score: CandidateScore,
        last_written_at: datetime | None,
        hold_reason: HoldReason | None,
        now: datetime,
        waiting_since: datetime | None = None,
    ) -> CompactionCandidate:
        """Create the candidate of a partition first found to need compaction: pending, or held by a filter."""
        return cls(
            id=CompactionCandidateId.for_partition(table_uuid, partition),
            table_uuid=table_uuid,
            partition=partition,
            label=label,
            state=CandidateState.PENDING if hold_reason is None else CandidateState.HELD,
            hold_reason=hold_reason,
            score=score,
            last_written_at=last_written_at,
            waiting_since=waiting_since,
            observed_at=now,
            updated_at=now,
        )

    def observe(  # noqa: PLR0913
        self,
        score: CandidateScore,
        last_written_at: datetime | None,
        hold_reason: HoldReason | None,
        now: datetime,
        *,
        waiting_since: datetime | None = None,
        label: str | None = None,
    ) -> None:
        """Take a new observation of a partition that still needs compaction.

        A claimed or running candidate whose lease is live keeps its claim and
        takes only the new score: its run may still be writing. Any other
        candidate (including one whose lease expired, or whose run finished) is
        pending again, or held when ``hold_reason`` says so.
        """
        observed = {
            "score": score,
            "last_written_at": last_written_at,
            "waiting_since": waiting_since,
            "observed_at": now,
            "updated_at": now,
            "label": self.label if label is None else label,
        }
        if self.state.holds_a_claim and self.lease_expires_at is not None and now < self.lease_expires_at:
            self._assign_together(**observed)
            return
        self._assign_together(
            **observed,
            state=CandidateState.PENDING if hold_reason is None else CandidateState.HELD,
            hold_reason=hold_reason,
            claimed_by_run_id=None,
            lease_expires_at=None,
        )

    def claim(self, run_id: TableMaintenanceRunId, lease_until: datetime, now: datetime) -> None:
        """Give a pending candidate to ``run_id`` until ``lease_until``."""
        if self.state is not CandidateState.PENDING:
            raise InvalidCandidateTransition(f"cannot claim a {self.state.value} candidate")
        if lease_until <= now:
            raise InvalidCandidateTransition("a claim's lease must end after the claim")
        self._assign_together(
            state=CandidateState.CLAIMED,
            claimed_by_run_id=run_id,
            lease_expires_at=lease_until,
            waiting_since=None,
            updated_at=now,
        )

    def start(self, run_id: TableMaintenanceRunId, now: datetime) -> None:
        """Mark the candidate claimed by ``run_id`` as being compacted; a running one stays running."""
        self._require_held_by(run_id, "start")
        if self.state is CandidateState.RUNNING:
            return
        if self.state is not CandidateState.CLAIMED:
            raise InvalidCandidateTransition(f"cannot start a {self.state.value} candidate")
        self._assign_together(state=CandidateState.RUNNING, updated_at=now)

    def finish(self, run_id: TableMaintenanceRunId, *, succeeded: bool, now: datetime) -> None:
        """End the claimed or running candidate of ``run_id`` as done or failed; anything else is left as it is."""
        if self.claimed_by_run_id != run_id or not self.state.holds_a_claim:
            return
        self._assign_together(
            state=CandidateState.DONE if succeeded else CandidateState.FAILED,
            lease_expires_at=None,
            updated_at=now,
        )

    def release(self, run_id: TableMaintenanceRunId, now: datetime) -> None:
        """Hand the candidate ``run_id`` holds back as pending; one its run finished stays finished."""
        self._require_held_by(run_id, "release")
        if self.state.finished:
            return
        self._assign_together(
            state=CandidateState.PENDING,
            claimed_by_run_id=None,
            lease_expires_at=None,
            updated_at=now,
        )

    def _require_held_by(self, run_id: TableMaintenanceRunId, command: str) -> None:
        if self.claimed_by_run_id != run_id:
            holder = "no run" if self.claimed_by_run_id is None else f"run {self.claimed_by_run_id.value}"
            raise InvalidCandidateTransition(
                f"cannot {command} for run {run_id.value} a {self.state.value} candidate held by {holder}"
            )
