"""Define the TableRowMapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from adapter.outbound.shared.sql import IsoDatetimeCodec, MaintenanceSettingsCodec
from application.domain.model.table_discovery_rule import TableDiscoveryRuleId
from application.domain.model.shared import MaintenanceOperation
from application.domain.model.table import (
    Table,
    OperationState,
    TableName,
    TableSelection,
    TableStatus,
    TableId,
)
from application.domain.model.table_maintenance_preset import TableMaintenancePresetId

if TYPE_CHECKING:
    from sqlalchemy import RowMapping


class TableRowMapper:
    """Convert between Table aggregates and table rows."""

    @staticmethod
    def to_values(table: Table) -> dict[str, Any]:
        """Return the column values of the aggregate."""
        return {
            "uuid": table.id.value,
            "catalog": table.name.catalog,
            "namespace": table.name.namespace,
            "table_name": table.name.table,
            "status": table.status.value,
            "selection": table.selection.value,
            "settings_json": (
                None
                if table.settings is None
                else MaintenanceSettingsCodec.encode(table.settings)
            ),
            "matched_rule_id": (
                None if table.matched_rule_id is None else table.matched_rule_id.value
            ),
            "source_preset_id": (
                None if table.source_preset_id is None else table.source_preset_id.value
            ),
            "registered_at": table.registered_at,
            "updated_at": table.updated_at,
            "operation_states_json": {
                op.value: {
                    "last_attempt_at": IsoDatetimeCodec.encode(state.last_attempt_at),
                    "consecutive_failures": state.consecutive_failures,
                }
                for op, state in table.operation_states.items()
            },
        }

    @staticmethod
    def to_aggregate(row: RowMapping) -> Table:
        """Rebuild the aggregate from a row without registering events."""
        settings = row["settings_json"]
        matched = row["matched_rule_id"]
        preset = row["source_preset_id"]
        return Table(
            id=TableId(row["uuid"]),
            name=TableName(
                catalog=row["catalog"],
                namespace=row["namespace"],
                table=row["table_name"],
            ),
            status=TableStatus(row["status"]),
            selection=TableSelection(row["selection"]),
            settings=None
            if settings is None
            else MaintenanceSettingsCodec.decode(settings),
            matched_rule_id=None if matched is None else TableDiscoveryRuleId(matched),
            source_preset_id=None
            if preset is None
            else TableMaintenancePresetId(preset),
            registered_at=row["registered_at"],
            updated_at=row["updated_at"],
            operation_states={
                MaintenanceOperation(op): OperationState(
                    last_attempt_at=IsoDatetimeCodec.decode(data["last_attempt_at"]),
                    consecutive_failures=data["consecutive_failures"],
                )
                for op, data in row["operation_states_json"].items()
            },
        )
