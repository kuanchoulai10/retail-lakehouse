"""Define the CompactionCandidate aggregate root."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from pydantic import NonNegativeInt, model_validator

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
from context.table_maintenance.application.domain.model.table_maintenance_policy import MaintenancePriority
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    TableMaintenanceRunId,
)

if TYPE_CHECKING:
    from collections.abc import Mapping


class CompactionCandidate(AggregateRoot[CompactionCandidateId]):
    """Hold one partition of a table that needs compaction, how much it is worth and who works on it.

    One candidate exists per table and partition (``PartitionKey.whole_table()``
    for a compaction of the whole table). Observation creates and re-scores it,
    with the priority of the table's policy; a compaction round grants the best
    pending ones across tables under a lease; the table's reconcile claims its
    granted ones for a run under a longer lease; the run starts them and
    finishes them; the next observation decides whether the partition is
    healthy (it leaves the candidates) or still needs work (it is pending
    again), whatever the run reported. A grant or claim whose lease expired is
    given up by the next observation.

    ``label`` names the partition for people (``field=value`` pairs).
    ``waiting_since`` is when the candidate started to wait for writes to its
    partition to stop; it is kept while writes go on and cleared once they
    stop or the candidate is claimed, so a partition written without pause is
    not held forever. ``claimed_by_run_id`` names the run that holds the
    candidate (claimed, running) or last held it (done, failed);
    ``granted_round_id`` names the round that granted it (granted) or the run
    its claim came from (claimed, running, done, failed). ``pending_since`` is
    when it last became pending; it is kept while it stays pending or granted,
    and through a ``not_due`` hold (a cooldown does not restart the wait), so
    ``overdue`` can tell how long it has waited for a run. A claim or a filter
    hold (too small, recently written) ends the wait.

    ``version`` is the stored version the candidate was read at, 0 for one
    never stored; the store refuses a save from a version it has moved past
    (``StaleCompactionCandidate``) and calls ``mark_saved`` after each save.
    """

    id: CompactionCandidateId
    table_uuid: TableId
    partition: PartitionKey
    label: str
    state: CandidateState
    hold_reason: HoldReason | None = None
    score: CandidateScore
    priority: MaintenancePriority = MaintenancePriority.P2
    last_written_at: datetime | None = None
    waiting_since: datetime | None = None
    observed_at: datetime
    claimed_by_run_id: TableMaintenanceRunId | None = None
    granted_round_id: str | None = None
    lease_expires_at: datetime | None = None
    pending_since: datetime | None = None
    updated_at: datetime
    version: NonNegativeInt = 0

    @model_validator(mode="after")
    def _state_agrees_with_hold_claim_and_lease(self) -> CompactionCandidate:
        """Reject a hold reason, grant, claim, lease or pending start the state does not allow."""
        if (self.state is CandidateState.HELD) != (self.hold_reason is not None):
            raise ValueError("a held candidate needs a hold reason, and only a held one has one")
        has_run = self.state.holds_a_claim or self.state.finished
        if has_run != (self.claimed_by_run_id is not None):
            raise ValueError(f"a {self.state.value} candidate {'needs' if has_run else 'has no'} run")
        if self.state.holds_a_lease != (self.lease_expires_at is not None):
            raise ValueError("a granted, claimed or running candidate needs a lease, and only such a candidate has one")
        if self.state is CandidateState.GRANTED and self.granted_round_id is None:
            raise ValueError("a granted candidate needs the round that granted it")
        if self.state in {CandidateState.PENDING, CandidateState.HELD} and self.granted_round_id is not None:
            raise ValueError(f"a {self.state.value} candidate has no grant")
        if self.pending_since is not None and not (self.state.awaits_a_run or self._held_not_due):
            raise ValueError(f"a {self.state.value} candidate is not waiting for a run")
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
        priority: MaintenancePriority = MaintenancePriority.P2,
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
            priority=priority,
            last_written_at=last_written_at,
            waiting_since=waiting_since,
            observed_at=now,
            pending_since=now if hold_reason is None else None,
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
        priority: MaintenancePriority | None = None,
    ) -> None:
        """Take a new observation of a partition that still needs compaction.

        A claimed or running candidate whose lease is live keeps its claim and
        takes only the new score and priority: its run may still be writing. A
        granted one whose lease is live keeps its grant the same way unless a
        filter holds it (too small, recently written): a partition being written
        must not be compacted, so the grant ends. A ``not_due`` observation keeps
        the grant, since nothing claims it while compaction is not due and the
        lease ends it soon. Any other candidate (including one whose lease
        expired, or whose run finished) is pending again, or held when
        ``hold_reason`` says so. ``priority`` is the applicable policy's (None
        keeps the one it has).
        """
        observed = {
            "score": score,
            "last_written_at": last_written_at,
            "waiting_since": waiting_since,
            "observed_at": now,
            "updated_at": now,
            "label": self.label if label is None else label,
            "priority": self.priority if priority is None else priority,
        }
        live = self.state.holds_a_lease and self.lease_expires_at is not None and now < self.lease_expires_at
        filtered = hold_reason not in {None, HoldReason.NOT_DUE}
        if live and (self.state is not CandidateState.GRANTED or not filtered):
            self._assign_together(**observed)
            return
        self._assign_together(
            **observed,
            state=CandidateState.PENDING if hold_reason is None else CandidateState.HELD,
            hold_reason=hold_reason,
            claimed_by_run_id=None,
            granted_round_id=None,
            lease_expires_at=None,
            pending_since=None if filtered else self._pending_since_kept(now, hold_reason),
        )

    def grant(self, round_id: str, lease_until: datetime, now: datetime) -> None:
        """Let the table's next run take this pending candidate, as compaction round ``round_id`` decided.

        The grant lasts until ``lease_until``; one its table did not claim by
        then is pending again at the next observation.
        """
        if self.state is not CandidateState.PENDING:
            raise InvalidCandidateTransition(f"cannot grant a {self.state.value} candidate")
        if lease_until <= now:
            raise InvalidCandidateTransition("a grant's lease must end after the grant")
        self._assign_together(
            state=CandidateState.GRANTED,
            granted_round_id=round_id,
            lease_expires_at=lease_until,
            pending_since=self._pending_since_from(now),
            updated_at=now,
        )

    def claim(self, run_id: TableMaintenanceRunId, lease_until: datetime, now: datetime) -> None:
        """Give a granted candidate to ``run_id`` until ``lease_until``, keeping the round that granted it."""
        if self.state is not CandidateState.GRANTED:
            raise InvalidCandidateTransition(f"cannot claim a {self.state.value} candidate")
        if self.lease_expires_at is not None and self.lease_expires_at <= now:
            raise InvalidCandidateTransition("cannot claim a candidate whose grant has ended")
        if lease_until <= now:
            raise InvalidCandidateTransition("a claim's lease must end after the claim")
        self._assign_together(
            state=CandidateState.CLAIMED,
            claimed_by_run_id=run_id,
            lease_expires_at=lease_until,
            waiting_since=None,
            pending_since=None,
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
        """Hand the candidate ``run_id`` holds back as pending; one its run finished stays finished.

        Both a ``claimed`` and a ``running`` candidate are handed back: a run that
        never started holds only claimed ones, but a run that ended without
        finishing its candidates (or never reported) can leave them running.
        """
        self._require_held_by(run_id, "release")
        if self.state.finished:
            return
        self._assign_together(
            state=CandidateState.PENDING,
            claimed_by_run_id=None,
            granted_round_id=None,
            lease_expires_at=None,
            pending_since=now,
            updated_at=now,
        )

    def overdue(self, sla: Mapping[MaintenancePriority, timedelta], now: datetime) -> bool:
        """Return whether the candidate has waited for a run longer than its priority's SLA.

        Only a pending or granted candidate waits; one without a recorded start
        (a row stored before the wait was recorded) is never overdue.
        """
        if not self.state.awaits_a_run or self.pending_since is None:
            return False
        return now - self.pending_since > sla[self.priority]

    def grant_expired(self, now: datetime) -> bool:
        """Return whether this is a grant whose lease ended unclaimed; the next observation makes it pending."""
        return (
            self.state is CandidateState.GRANTED and self.lease_expires_at is not None and now >= self.lease_expires_at
        )

    def keeps_its_table_busy(self, now: datetime) -> bool:
        """Return whether this candidate holds its table's compaction, so a round should grant the table nothing.

        A live grant, claim or run holds it: the table's next run is already
        decided. So does a finished candidate until the next observation, which
        comes after the run and decides what is left; until then the table's
        other candidates still show the state from before the run.
        """
        if self.state.finished:
            return True
        return self.state.holds_a_lease and self.lease_expires_at is not None and now < self.lease_expires_at

    def mark_saved(self) -> None:
        """Take the version the store gave the candidate's row: one past the version it was read at."""
        self.version = self.version + 1

    @property
    def _held_not_due(self) -> bool:
        return self.state is CandidateState.HELD and self.hold_reason is HoldReason.NOT_DUE

    def _pending_since_from(self, now: datetime) -> datetime:
        """Keep the start of a wait already going on (pending, granted or not due), or start one now."""
        if (self.state.awaits_a_run or self._held_not_due) and self.pending_since is not None:
            return self.pending_since
        return now

    def _pending_since_kept(self, now: datetime, hold_reason: HoldReason | None) -> datetime | None:
        """Return the wait to keep for a pending or not-due observation; a not-due one never starts a wait."""
        if hold_reason is None:
            return self._pending_since_from(now)
        if self.state.awaits_a_run or self._held_not_due:
            return self.pending_since
        return None

    def _require_held_by(self, run_id: TableMaintenanceRunId, command: str) -> None:
        if self.claimed_by_run_id != run_id:
            holder = "no run" if self.claimed_by_run_id is None else f"run {self.claimed_by_run_id.value}"
            raise InvalidCandidateTransition(
                f"cannot {command} for run {run_id.value} a {self.state.value} candidate held by {holder}"
            )
