"""Define the candidate_policy_targets domain service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import PolicyTarget, PolicyTargetType
from context.table_maintenance.application.domain.service.shared.enclosing_policy_targets import (
    enclosing_policy_targets,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.table import TableName


def candidate_policy_targets(name: TableName, table_uuid: str) -> tuple[PolicyTarget, ...]:
    """Return where a policy may be attached for a table, most specific first.

    The table itself, then each namespace prefix from deepest to shallowest, then the catalog.
    """
    table = PolicyTarget(
        type=PolicyTargetType.TABLE,
        path=(name.catalog, *name.namespace.split("."), name.table),
        table_uuid=table_uuid,
    )
    return (table, *enclosing_policy_targets(name.catalog, name.namespace))
