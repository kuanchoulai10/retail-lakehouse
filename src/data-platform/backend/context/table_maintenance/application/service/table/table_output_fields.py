"""Define the table_output_fields function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime

    from context.table_maintenance.application.domain.model.table import OperationState, Table


def _attention_fields(state: OperationState, policy_names: Mapping[str, str]) -> dict[str, Any] | None:
    mark = state.attention
    if mark is None:
        return None
    policy_id = mark.policy.policy_id.value
    return {
        "since": mark.since,
        "reason": mark.reason,
        "policy_id": policy_id,
        "policy_name": policy_names.get(policy_id, mark.policy_name.value),
        "policy_deleted": policy_id not in policy_names,
        "policy_version": mark.policy.version,
    }


def table_output_fields(
    table: Table, catalog_discovered_at: datetime | None, policy_names: Mapping[str, str]
) -> dict[str, Any]:
    """Return the primitive fields shared by every table output.

    ``catalog_discovered_at`` is the last discovery of the table's catalog, None
    when it was never discovered; the table's last discovery is derived from it.
    ``policy_names`` maps a policy id to its current name; a needs-attention mark
    shows its policy's id and that name, or, when the policy was deleted since
    (``policy_deleted``), the name the mark kept when it was set.
    """
    return {
        "uuid": table.id.value,
        "catalog": table.name.catalog,
        "namespace": table.name.namespace,
        "table": table.name.table,
        "status": table.status.value,
        "priority": table.priority.value,
        "matched_rule_id": (None if table.matched_rule_id is None else table.matched_rule_id.value),
        "matched_policy_id": table.discovered_by.policy_id.value,
        "matched_policy_version": table.discovered_by.policy_version,
        "operation_states": {
            op.value: {
                "last_attempt_at": state.last_attempt_at,
                "consecutive_failures": state.consecutive_failures,
                "last_successful_size": state.last_successful_size and state.last_successful_size.value,
                "needs_attention": _attention_fields(state, policy_names),
            }
            for op, state in table.operation_states.items()
        },
        "registered_at": table.registered_at,
        "updated_at": table.updated_at,
        "last_committed_at": table.last_committed_at,
        "last_discovered_at": table.last_discovered(catalog_discovered_at),
    }
