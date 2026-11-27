"""Define the Table aggregate root."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import Field, PositiveInt

from base import AggregateRoot, ReadOnlyMapping
from context.table_maintenance.application.domain.model.shared import (
    ComputeSize,
    MaintenanceOperation,
    OverTargetPartition,
    TableId,
    TablePriority,
)
from context.table_maintenance.application.domain.model.table.invalid_table_transition import (
    InvalidTableTransition,
)
from context.table_maintenance.application.domain.model.table.operation_state import (
    OperationState,
)
from context.table_maintenance.application.domain.model.table.table_name import (
    TableName,
)
from context.table_maintenance.application.domain.model.table.table_status import (
    TableStatus,
)
from context.table_maintenance.application.domain.model.table_discovery_policy import (
    DecidedBy,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from context.table_maintenance.application.domain.model.table.applied_policy_ref import (
        AppliedPolicyRef,
    )
    from context.table_maintenance.application.domain.model.table.attention_mark import (
        AttentionMark,
    )
    from context.table_maintenance.application.domain.model.table.recorded_attempt import (
        RecordedAttempt,
    )
    from context.table_maintenance.application.domain.model.table_discovery_policy import ManagementDecision


class Table(AggregateRoot[TableId]):
    """Hold the maintenance state of one Iceberg table, identified by its uuid.

    Its nearest discovery policy alone decides whether a table is managed: ``manage`` and
    ``unmanage`` apply that decision, and an unmanaged table keeps its row, so its history
    and per-operation state survive. ``decided_by`` names what decided it, managed or not:
    the policy, its version and the position of the deciding rule (None when no rule
    matched). It is None when no discovery policy applies, which leaves the table unmanaged.

    ``priority`` says how urgently the table's maintenance is scheduled; it starts at P3.

    ``last_committed_at`` is the newest commit seen in the catalog, None until one is
    seen. ``last_discovered_at`` is stamped when the table is dropped: the last time
    discovery saw it. A live table takes its catalog's last discovery instead (see
    ``last_discovered``), so a discovery need not save every table it sees. Neither
    is a change of maintenance state, so neither moves ``updated_at``.

    ``over_target_partitions`` holds the partitions the last scheduled plan found over their
    compaction target, each with the time the first plan saw it over. It is replaced whole by
    ``record_over_target_partitions`` and does not move ``updated_at`` either.

    ``version`` is the stored version the table was read at, 1 for a table never saved
    since its registration. Only the repository moves it: a save made from a copy read at an
    older version is refused, so no writer silently puts back what another one stored since.
    """

    id: TableId
    name: TableName
    status: TableStatus
    decided_by: DecidedBy | None
    registered_at: datetime
    updated_at: datetime
    operation_states: ReadOnlyMapping[MaintenanceOperation, OperationState] = Field(default_factory=dict)
    last_committed_at: datetime | None = None
    last_discovered_at: datetime | None = None
    priority: TablePriority = TablePriority.P3
    over_target_partitions: tuple[OverTargetPartition, ...] = ()
    version: PositiveInt = 1

    @classmethod
    def register(
        cls,
        id: TableId,  # noqa: A002
        name: TableName,
        decision: ManagementDecision,
        now: datetime,
    ) -> Table:
        """Register a discovered table, managed or unmanaged as the decision says, recording what decided it."""
        return cls(
            id=id,
            name=name,
            status=TableStatus.MANAGED if decision.manage else TableStatus.UNMANAGED,
            decided_by=decision.decided_by,
            registered_at=now,
            updated_at=now,
        )

    @property
    def is_managed(self) -> bool:
        """Return whether the table is managed, so it has a reconciliation workflow."""
        return self.status == TableStatus.MANAGED

    def operation_state(self, op: MaintenanceOperation) -> OperationState:
        """Return the state of one operation, empty if never attempted."""
        return self.operation_states.get(op, OperationState())

    def _ensure_not_dropped(self) -> None:
        if self.status == TableStatus.DROPPED:
            raise InvalidTableTransition("table is dropped")

    def manage(self, decided_by: DecidedBy, now: datetime) -> None:
        """Manage the table under the policy and rule that decide it; idempotent for an equal decider."""
        self._decide(TableStatus.MANAGED, decided_by, now)

    def unmanage(self, decided_by: DecidedBy | None, now: datetime) -> None:
        """Stop managing the table, keeping its row; idempotent for an equal decider.

        ``decided_by`` is None when no discovery policy applies to the table any more.
        """
        self._decide(TableStatus.UNMANAGED, decided_by, now)

    def _decide(self, status: TableStatus, decided_by: DecidedBy | None, now: datetime) -> None:
        self._ensure_not_dropped()
        if self.status == status and self.decided_by == decided_by:
            return
        self._assign_together(status=status, decided_by=decided_by, updated_at=now)

    def set_priority(self, priority: TablePriority, now: datetime) -> None:
        """Set how urgently the table's maintenance is scheduled; idempotent."""
        self._ensure_not_dropped()
        if self.priority == priority:
            return
        self._assign_together(priority=priority, updated_at=now)

    def mark_dropped(self, now: datetime, *, catalog_discovered_at: datetime | None = None) -> None:
        """Mark the table dropped; terminal and idempotent.

        ``catalog_discovered_at`` is the last discovery of its catalog before the one
        that missed the table; the table keeps the last time discovery saw it.
        """
        if self.status == TableStatus.DROPPED:
            return
        self._assign_together(
            status=TableStatus.DROPPED,
            updated_at=now,
            last_discovered_at=self.last_discovered(catalog_discovered_at),
        )

    def last_discovered(self, catalog_discovered_at: datetime | None) -> datetime | None:
        """Return when discovery last saw the table, given its catalog's last discovery.

        A dropped table answers the time stamped when it was dropped. A live one was
        seen by its catalog's last discovery, or when it was registered if that came
        later (a catalog event registers a table between discoveries); with no
        discovery of its catalog the time is unknown.
        """
        if self.status == TableStatus.DROPPED:
            return self.last_discovered_at
        if catalog_discovered_at is None:
            return None
        return max(catalog_discovered_at, self.registered_at)

    def record_last_commit(self, at: datetime | None) -> bool:
        """Record a commit seen in the catalog; return whether the last commit moved.

        The last commit only moves forward: an older or equal time, or None (no commit
        yet), changes nothing, and neither does any time once the table is dropped.
        """
        if at is None or self.status == TableStatus.DROPPED:
            return False
        if self.last_committed_at is not None and at <= self.last_committed_at:
            return False
        self.last_committed_at = at
        return True

    def record_over_target_partitions(self, partitions: Sequence[OverTargetPartition]) -> bool:
        """Replace the partitions held over the target; return whether the record changed.

        An equal record, or any record once the table is dropped, changes nothing. The record is
        compared as given, so a caller passes it in one fixed order. ``updated_at`` does not move.
        """
        record = tuple(partitions)
        if self.status == TableStatus.DROPPED or record == self.over_target_partitions:
            return False
        self.over_target_partitions = record
        return True

    def rename(self, name: TableName, now: datetime) -> None:
        """Change the table's name, keeping its identity."""
        self._ensure_not_dropped()
        self.name = name
        self.updated_at = now

    def record_operation_result(
        self,
        op: MaintenanceOperation,
        succeeded: bool,
        at: datetime,
        *,
        size: ComputeSize | None = None,
        fits_smaller: bool = False,
        attempt: RecordedAttempt | None = None,
    ) -> None:
        """Record an operation outcome, the size a success ran at and whether it would have fit a smaller one.

        A success needs its ``size``; a failure takes none. Allowed in any non-dropped status. Given
        the ``attempt`` the outcome belongs to, the outcome of the attempt taken in last changes
        nothing again, so a retried record counts once.
        """
        self._ensure_not_dropped()
        if attempt is not None and self.has_recorded(op, attempt):
            return
        state = self.operation_state(op)
        if succeeded:
            if size is None:
                msg = f"a success of {op} needs the size it ran at"
                raise ValueError(msg)
            updated = state.after_success(at, size, fits_smaller=fits_smaller)
        else:
            updated = state.after_failure(at)
        if attempt is not None:
            updated = updated.recorded(attempt)
        self._set_operation_state(op, updated, at)

    def has_recorded(self, op: MaintenanceOperation, attempt: RecordedAttempt) -> bool:
        """Return whether the outcome of ``attempt`` was the last one taken in for ``op``."""
        return self.operation_state(op).last_recorded == attempt

    def mark_needs_attention(self, op: MaintenanceOperation, mark: AttentionMark, at: datetime) -> None:
        """Mark an operation as needing a person; reconcile stops planning it under the mark's policy."""
        self._ensure_not_dropped()
        self._set_operation_state(op, self.operation_state(op).with_attention(mark), at)

    def clear_needs_attention(self, op: MaintenanceOperation, at: datetime) -> None:
        """Lift an operation's needs-attention mark; a no-op when it has none."""
        self._ensure_not_dropped()
        state = self.operation_state(op)
        if state.attention is None:
            return
        self._set_operation_state(op, state.without_attention(), at)

    def lift_attention_set_under_another_policy(
        self, applied: AppliedPolicyRef, at: datetime
    ) -> list[MaintenanceOperation]:
        """Lift every needs-attention mark set under a policy other than ``applied``; return the operations lifted.

        A change of the table's applicable policy (another policy, version or target) clears the
        marks set before it, for good: the earlier policy applying again does not bring them back.
        """
        self._ensure_not_dropped()
        lifted = [
            op
            for op, state in self.operation_states.items()
            if state.attention is not None and not state.needs_attention_under(applied)
        ]
        for op in lifted:
            self._set_operation_state(op, self.operation_state(op).without_attention(), at)
        return lifted

    def _set_operation_state(self, op: MaintenanceOperation, state: OperationState, at: datetime) -> None:
        self.operation_states = {**self.operation_states, op: state}
        self.updated_at = at
