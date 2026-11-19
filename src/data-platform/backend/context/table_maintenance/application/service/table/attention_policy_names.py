"""Define the attention_policy_names function."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from context.table_maintenance.application.domain.model.table import Table
    from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
        TableMaintenancePoliciesRepo,
    )


def attention_policy_names(tables: Iterable[Table], policies_repo: TableMaintenancePoliciesRepo) -> dict[str, str]:
    """Return the current name of each policy a needs-attention mark of the tables points at, keyed by its id.

    A policy deleted since its mark was set is missing from the result, so the mark shows the
    name it kept when it was set.
    """
    ids = {
        state.attention.policy.policy_id: None
        for table in tables
        for state in table.operation_states.values()
        if state.attention is not None
    }
    if not ids:
        return {}
    return {policy.id.value: policy.name.value for policy in policies_repo.get_many(list(ids))}
