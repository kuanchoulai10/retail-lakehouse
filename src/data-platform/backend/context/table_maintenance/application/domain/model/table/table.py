"""Define the Table aggregate root."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import Field

from base import AggregateRoot
from context.table_maintenance.application.domain.model.shared import ComputeSize, MaintenanceOperation
from context.table_maintenance.application.domain.model.table.invalid_table_transition import (
    InvalidTableTransition,
)
from context.table_maintenance.application.domain.model.table.operation_state import (
    OperationState,
)
from context.table_maintenance.application.domain.model.table.table_id import TableId
from context.table_maintenance.application.domain.model.table.table_name import (
    TableName,
)
from context.table_maintenance.application.domain.model.table.table_status import (
    TableStatus,
)
from context.table_maintenance.application.domain.model.table_discovery_rules import (
    TableDiscoveryRuleId,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.table.attention_mark import (
        AttentionMark,
    )


class Table(AggregateRoot[TableId]):
    """Hold the maintenance state of one Iceberg table, identified by its uuid.

    The discovery rules alone decide whether a table is managed: ``manage`` and
    ``unmanage`` apply their decision, and an unmanaged table keeps its row, so
    its history and per-operation state survive.
    """

    id: TableId
    name: TableName
    status: TableStatus
    matched_rule_id: TableDiscoveryRuleId | None
    registered_at: datetime
    updated_at: datetime
    operation_states: dict[MaintenanceOperation, OperationState] = Field(default_factory=dict)

    @classmethod
    def register(
        cls,
        id: TableId,  # noqa: A002
        name: TableName,
        rule_id: TableDiscoveryRuleId,
        now: datetime,
    ) -> Table:
        """Register a table a discovery rule includes, as managed."""
        return cls(
            id=id,
            name=name,
            status=TableStatus.MANAGED,
            matched_rule_id=rule_id,
            registered_at=now,
            updated_at=now,
        )

    @classmethod
    def register_unmanaged(
        cls,
        id: TableId,  # noqa: A002
        name: TableName,
        now: datetime,
    ) -> Table:
        """Register a table no discovery rule includes, as unmanaged."""
        return cls(
            id=id,
            name=name,
            status=TableStatus.UNMANAGED,
            matched_rule_id=None,
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

    def manage(self, rule_id: TableDiscoveryRuleId, now: datetime) -> None:
        """Manage the table under the include rule that decides it; idempotent for that rule."""
        self._ensure_not_dropped()
        if self.status == TableStatus.MANAGED and self.matched_rule_id == rule_id:
            return
        self._assign_together(status=TableStatus.MANAGED, matched_rule_id=rule_id, updated_at=now)

    def unmanage(self, now: datetime) -> None:
        """Stop managing the table, keeping its row; idempotent."""
        self._ensure_not_dropped()
        if self.status == TableStatus.UNMANAGED:
            return
        self._assign_together(status=TableStatus.UNMANAGED, matched_rule_id=None, updated_at=now)

    def mark_dropped(self, now: datetime) -> None:
        """Mark the table dropped; terminal and idempotent."""
        if self.status == TableStatus.DROPPED:
            return
        self.status = TableStatus.DROPPED
        self.updated_at = now

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
    ) -> None:
        """Record an operation outcome, and the size a success ran at; allowed in any non-dropped status."""
        self._ensure_not_dropped()
        state = self.operation_state(op)
        self._set_operation_state(op, state.after_success(at, size) if succeeded else state.after_failure(at), at)

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

    def _set_operation_state(self, op: MaintenanceOperation, state: OperationState, at: datetime) -> None:
        self.operation_states = {**self.operation_states, op: state}
        self.updated_at = at
