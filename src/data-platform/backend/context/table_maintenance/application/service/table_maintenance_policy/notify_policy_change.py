"""Define the notify_policy_change function."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table import TableChange, TableStatus
from context.table_maintenance.application.domain.model.table_maintenance_policy import DEFAULT_POLICY_ID
from context.table_maintenance.application.domain.service.shared import nearest_maintenance_policy
from context.table_maintenance.application.port.outbound.table import SendTableChangeGatewayInput

if TYPE_CHECKING:
    from collections.abc import Callable

    from context.table_maintenance.application.domain.model.namespace import Namespace
    from context.table_maintenance.application.domain.model.table import Table
    from context.table_maintenance.application.port.outbound.catalog import CatalogsRepo
    from context.table_maintenance.application.port.outbound.namespace import NamespacesRepo
    from context.table_maintenance.application.port.outbound.table import SendTableChangeGateway, TablesRepo
    from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
        TableMaintenancePoliciesRepo,
    )

logger = logging.getLogger(__name__)

type _ResolvedPolicies = dict[str, tuple[Table, tuple[str, int | None]]]


def notify_policy_change[T](  # noqa: PLR0913
    tables_repo: TablesRepo,
    policies_repo: TableMaintenancePoliciesRepo,
    catalogs_repo: CatalogsRepo,
    namespaces_repo: NamespacesRepo,
    table_changes: SendTableChangeGateway,
    change: Callable[[], T],
) -> T:
    """Run ``change``, then tell every managed table whose applicable policy (by id) or version moved.

    The applicable policy of each managed table is resolved before and after the change with
    ``nearest_maintenance_policy`` over the tables, every namespace and every catalog, the platform
    default when none holds one; a table whose result differs gets a ``policy_changed`` table change.
    A change that raises tells no table. Sending is best effort: the change has already been
    committed, the next reconciliation resolves the policy anyway, so a send that fails is logged
    and the other tables are still told.
    """
    before = _resolve(tables_repo, policies_repo, catalogs_repo, namespaces_repo)
    result = change()
    after = _resolve(tables_repo, policies_repo, catalogs_repo, namespaces_repo)
    for table_id, (table, resolved) in after.items():
        if table_id in before and before[table_id][1] != resolved:
            _send(table_changes, table)
    return result


def _resolve(
    tables_repo: TablesRepo,
    policies_repo: TableMaintenancePoliciesRepo,
    catalogs_repo: CatalogsRepo,
    namespaces_repo: NamespacesRepo,
) -> _ResolvedPolicies:
    catalogs = {c.id.value: c for c in catalogs_repo.list_all()}
    namespaces: dict[str, list[Namespace]] = defaultdict(list)
    for namespace in namespaces_repo.list_all():
        namespaces[namespace.catalog].append(namespace)
    versions = {p.id.value: p.version for p in policies_repo.list_all()}
    resolved: _ResolvedPolicies = {}
    for table in tables_repo.list_by_statuses([TableStatus.MANAGED]):
        catalog = table.name.catalog
        nearest = nearest_maintenance_policy(table, namespaces[catalog], catalogs.get(catalog))
        policy_id = DEFAULT_POLICY_ID.value if nearest is None else nearest.policy_id.value
        resolved[table.id.value] = (table, (policy_id, versions.get(policy_id)))
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
