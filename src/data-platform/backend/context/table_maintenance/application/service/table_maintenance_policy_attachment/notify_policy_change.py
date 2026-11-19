"""Define the notify_policy_change function."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table import TableChange, TableStatus
from context.table_maintenance.application.domain.model.table_maintenance_policy import DEFAULT_POLICY_NAME
from context.table_maintenance.application.domain.service.table_maintenance_policy_attachment import (
    candidate_policy_targets,
)
from context.table_maintenance.application.port.outbound.table import SendTableChangeGatewayInput

if TYPE_CHECKING:
    from collections.abc import Callable

    from context.table_maintenance.application.domain.model.table import Table
    from context.table_maintenance.application.port.outbound.table import SendTableChangeGateway, TablesRepo
    from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
        TableMaintenancePoliciesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_policy_attachment import (
        TableMaintenancePolicyAttachmentsRepo,
    )

logger = logging.getLogger(__name__)

type _ResolvedPolicies = dict[str, tuple[str, int | None]]


def notify_policy_change[T](
    tables_repo: TablesRepo,
    policies_repo: TableMaintenancePoliciesRepo,
    attachments_repo: TableMaintenancePolicyAttachmentsRepo,
    table_changes: SendTableChangeGateway,
    change: Callable[[], T],
) -> T:
    """Run ``change``, then tell every managed table whose applicable policy name or version moved.

    The applicable policy of each managed table is resolved before and after the change; a table
    whose result differs gets a ``policy_changed`` table change. Sending is best effort: the change
    has already been committed, the next reconciliation resolves the policy anyway, so a send that
    fails is logged and the other tables are still told.
    """
    tables = tables_repo.list_by_statuses([TableStatus.MANAGED])
    before = _resolve(tables, policies_repo, attachments_repo)
    result = change()
    after = _resolve(tables, policies_repo, attachments_repo)
    for table in tables:
        if before[table.id.value] != after[table.id.value]:
            _send(table_changes, table)
    return result


def _resolve(
    tables: list[Table],
    policies_repo: TableMaintenancePoliciesRepo,
    attachments_repo: TableMaintenancePolicyAttachmentsRepo,
) -> _ResolvedPolicies:
    attached = {a.target.key(): a.policy_name.value for a in attachments_repo.list_all()}
    versions = {p.id.value: p.version for p in policies_repo.list_all()}
    resolved: _ResolvedPolicies = {}
    for table in tables:
        candidates = candidate_policy_targets(table.name, table.id.value)
        name = next((attached[c.key()] for c in candidates if c.key() in attached), None)
        name = DEFAULT_POLICY_NAME if name is None else name
        resolved[table.id.value] = (name, versions.get(name))
    return resolved


def _send(table_changes: SendTableChangeGateway, table: Table) -> None:
    try:
        table_changes.send(
            SendTableChangeGatewayInput(
                table_uuid=table.id.value,
                table_name=table.name.fully_qualified(),
                change=TableChange.POLICY_CHANGED.value,
                is_managed=table.is_managed,
            )
        )
    except Exception:
        logger.exception("could not tell table %s that its maintenance policy changed", table.name.fully_qualified())
