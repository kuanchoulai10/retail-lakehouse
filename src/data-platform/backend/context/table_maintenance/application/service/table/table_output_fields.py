"""Define the table_output_fields function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.table import Table


def table_output_fields(table: Table) -> dict[str, Any]:
    """Return the primitive fields shared by every table output."""
    return {
        "uuid": table.id.value,
        "catalog": table.name.catalog,
        "namespace": table.name.namespace,
        "table": table.name.table,
        "status": table.status.value,
        "selection": table.selection.value,
        "settings": (None if table.settings is None else table.settings.to_primitives()),
        "matched_rule_id": (None if table.matched_rule_id is None else table.matched_rule_id.value),
        "source_preset_id": (None if table.source_preset_id is None else table.source_preset_id.value),
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
