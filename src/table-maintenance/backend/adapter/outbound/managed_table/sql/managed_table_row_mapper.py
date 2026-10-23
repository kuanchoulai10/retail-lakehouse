"""Define the ManagedTableRowMapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from adapter.outbound.sql.iso_datetime_codec import IsoDatetimeCodec
from adapter.outbound.sql.maintenance_settings_codec import MaintenanceSettingsCodec
from application.domain.model.discovery_rule.discovery_rule_id import DiscoveryRuleId
from application.domain.model.maintenance.maintenance_operation import (
    MaintenanceOperation,
)
from application.domain.model.managed_table.managed_table import ManagedTable
from application.domain.model.managed_table.operation_state import OperationState
from application.domain.model.managed_table.table_name import TableName
from application.domain.model.managed_table.table_selection import TableSelection
from application.domain.model.managed_table.table_status import TableStatus
from application.domain.model.managed_table.table_uuid import TableUuid
from application.domain.model.policy_template.policy_template_id import (
    PolicyTemplateId,
)

if TYPE_CHECKING:
    from sqlalchemy import RowMapping


class ManagedTableRowMapper:
    """Convert between ManagedTable aggregates and table rows."""

    @staticmethod
    def to_values(table: ManagedTable) -> dict[str, Any]:
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
            "source_template_id": (
                None
                if table.source_template_id is None
                else table.source_template_id.value
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
    def to_aggregate(row: RowMapping) -> ManagedTable:
        """Rebuild the aggregate from a row without registering events."""
        settings = row["settings_json"]
        matched = row["matched_rule_id"]
        template = row["source_template_id"]
        return ManagedTable(
            id=TableUuid(row["uuid"]),
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
            matched_rule_id=None if matched is None else DiscoveryRuleId(matched),
            source_template_id=None if template is None else PolicyTemplateId(template),
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
