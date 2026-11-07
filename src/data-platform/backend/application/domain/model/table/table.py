"""Define the Table aggregate root."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from application.domain.model.shared import MaintenanceOperation, MaintenanceSettings
from application.domain.model.table.invalid_table_transition import (
    InvalidTableTransition,
)
from application.domain.model.table.operation_state import OperationState
from application.domain.model.table.table_name import TableName
from application.domain.model.table.table_selection import TableSelection
from application.domain.model.table.table_status import TableStatus
from application.domain.model.table.table_id import TableId
from application.domain.model.table_maintenance_preset import TableMaintenancePresetId
from base import AggregateRoot

if TYPE_CHECKING:
    from application.domain.model.table_discovery_rule import TableDiscoveryRuleId


@dataclass(eq=False)
class Table(AggregateRoot[TableId]):
    """Hold the maintenance state of one Iceberg table, identified by its uuid."""

    id: TableId
    name: TableName
    status: TableStatus
    selection: TableSelection
    settings: MaintenanceSettings | None
    matched_rule_id: TableDiscoveryRuleId | None
    source_preset_id: TableMaintenancePresetId | None
    registered_at: datetime
    updated_at: datetime
    operation_states: dict[MaintenanceOperation, OperationState] = field(
        default_factory=dict
    )

    @classmethod
    def register_auto(
        cls,
        id: TableId,  # noqa: A002
        name: TableName,
        rule_id: TableDiscoveryRuleId,
        preset_id: TableMaintenancePresetId,
        settings: MaintenanceSettings,
        now: datetime,
    ) -> Table:
        """Register a table selected by a discovery rule."""
        return cls(
            id=id,
            name=name,
            status=TableStatus.ACTIVE,
            selection=TableSelection.AUTO,
            settings=settings,
            matched_rule_id=rule_id,
            source_preset_id=preset_id,
            registered_at=now,
            updated_at=now,
        )

    @classmethod
    def include_manual(
        cls,
        id: TableId,  # noqa: A002
        name: TableName,
        preset_id: TableMaintenancePresetId,
        settings: MaintenanceSettings,
        now: datetime,
    ) -> Table:
        """Register a table included by hand."""
        return cls(
            id=id,
            name=name,
            status=TableStatus.ACTIVE,
            selection=TableSelection.MANUAL,
            settings=settings,
            matched_rule_id=None,
            source_preset_id=preset_id,
            registered_at=now,
            updated_at=now,
        )

    @classmethod
    def exclude_manual(
        cls,
        id: TableId,  # noqa: A002
        name: TableName,
        now: datetime,
    ) -> Table:
        """Register a table excluded by hand, without settings."""
        return cls(
            id=id,
            name=name,
            status=TableStatus.EXCLUDED,
            selection=TableSelection.MANUAL,
            settings=None,
            matched_rule_id=None,
            source_preset_id=None,
            registered_at=now,
            updated_at=now,
        )

    @property
    def is_enrolled(self) -> bool:
        """Return whether the table is enrolled in maintenance (ACTIVE or PAUSED)."""
        return self.status in (TableStatus.ACTIVE, TableStatus.PAUSED)

    def operation_state(self, op: MaintenanceOperation) -> OperationState:
        """Return the state of one operation, empty if never attempted."""
        return self.operation_states.get(op, OperationState())

    def _ensure_not_dropped(self) -> None:
        if self.status == TableStatus.DROPPED:
            raise InvalidTableTransition("table is dropped")

    def pause(self, now: datetime) -> None:
        """Pause an active table; a paused table stays paused."""
        self._ensure_not_dropped()
        if self.status == TableStatus.EXCLUDED:
            raise InvalidTableTransition("cannot pause an excluded table")
        if self.status == TableStatus.PAUSED:
            return
        self.status = TableStatus.PAUSED
        self.updated_at = now

    def resume(self, now: datetime) -> None:
        """Resume a paused table; an active table stays active."""
        self._ensure_not_dropped()
        if self.status == TableStatus.EXCLUDED:
            raise InvalidTableTransition("cannot resume an excluded table")
        if self.status == TableStatus.ACTIVE:
            return
        self.status = TableStatus.ACTIVE
        self.updated_at = now

    def exclude(self, now: datetime) -> None:
        """Exclude the table by hand."""
        self._ensure_not_dropped()
        self.status = TableStatus.EXCLUDED
        self.selection = TableSelection.MANUAL
        self.updated_at = now

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

    def reset_to_auto(self, now: datetime) -> None:
        """Hand the table back to discovery rules."""
        self._ensure_not_dropped()
        self.selection = TableSelection.AUTO
        self.updated_at = now

    def include_manually(
        self,
        preset_id: TableMaintenancePresetId,
        settings: MaintenanceSettings,
        now: datetime,
    ) -> None:
        """Activate the table by hand with the given settings."""
        self._ensure_not_dropped()
        self.status = TableStatus.ACTIVE
        self.selection = TableSelection.MANUAL
        self.settings = settings
        self.source_preset_id = preset_id
        self.matched_rule_id = None
        self.updated_at = now

    def apply_auto_decision(
        self,
        rule_id: TableDiscoveryRuleId | None,
        preset_id: TableMaintenancePresetId | None,
        settings: MaintenanceSettings | None,
        now: datetime,
    ) -> None:
        """Apply a discovery rule decision to an AUTO table; MANUAL tables are ignored.

        An include decision carries a preset and settings; no rule, or an exclude
        rule (no preset), excludes the table and keeps its settings.
        """
        self._ensure_not_dropped()
        if self.selection != TableSelection.AUTO:
            return
        if preset_id is not None and self.settings is None and settings is None:
            raise InvalidTableTransition(
                "an include decision needs settings for a table without settings"
            )
        self.matched_rule_id = rule_id
        if preset_id is None:
            self.status = TableStatus.EXCLUDED
        else:
            if self.status == TableStatus.EXCLUDED:
                self.status = TableStatus.ACTIVE
            if self.settings is None:
                self.settings = settings
                self.source_preset_id = preset_id
        self.updated_at = now

    def update_settings(self, settings: MaintenanceSettings, now: datetime) -> None:
        """Replace the settings; an excluded table without settings cannot take them."""
        self._ensure_not_dropped()
        if self.status == TableStatus.EXCLUDED and self.settings is None:
            raise InvalidTableTransition("an excluded table has no settings to update")
        self.settings = settings
        self.updated_at = now

    def record_operation_result(
        self, op: MaintenanceOperation, succeeded: bool, at: datetime
    ) -> None:
        """Record an operation outcome; allowed in any non-dropped status."""
        self._ensure_not_dropped()
        state = self.operation_state(op)
        self.operation_states[op] = (
            state.after_success(at) if succeeded else state.after_failure(at)
        )
        self.updated_at = at
