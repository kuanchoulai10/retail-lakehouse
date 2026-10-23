"""Define the managed_table_output_fields function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from application.service.maintenance_settings.maintenance_settings_to_dict import (
    maintenance_settings_to_dict,
)

if TYPE_CHECKING:
    from application.domain.model.managed_table.managed_table import ManagedTable


def managed_table_output_fields(table: ManagedTable) -> dict[str, Any]:
    """Return the primitive fields shared by every managed table output."""
    return {
        "uuid": table.id.value,
        "catalog": table.name.catalog,
        "namespace": table.name.namespace,
        "table": table.name.table,
        "status": table.status.value,
        "selection": table.selection.value,
        "settings": (
            None
            if table.settings is None
            else maintenance_settings_to_dict(table.settings)
        ),
        "matched_rule_id": (
            None if table.matched_rule_id is None else table.matched_rule_id.value
        ),
        "source_template_id": (
            None if table.source_template_id is None else table.source_template_id.value
        ),
        "operation_states": {
            op.value: {
                "last_attempt_at": state.last_attempt_at,
                "consecutive_failures": state.consecutive_failures,
            }
            for op, state in table.operation_states.items()
        },
        "registered_at": table.registered_at,
        "updated_at": table.updated_at,
    }
