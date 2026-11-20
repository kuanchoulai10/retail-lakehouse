"""Define the apply_discovery_to_known_table function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table import (
    TableChange,
    TableManagementChange,
)
from context.table_maintenance.application.domain.service.table import (
    decide_table_management,
)
from context.table_maintenance.application.port.outbound.table import (
    SendTableChangeGatewayInput,
)
from context.table_maintenance.application.service.table.known_table_outcome import (
    KnownTableOutcome,
)

if TYPE_CHECKING:
    from datetime import datetime

    from context.table_maintenance.application.domain.model.table import (
        Table,
        TableName,
    )
    from context.table_maintenance.application.domain.model.table_discovery_rules import (
        TableDiscoveryRules,
    )
    from context.table_maintenance.application.port.outbound.table import (
        SendTableChangeGateway,
        TablesRepo,
    )


def apply_discovery_to_known_table(  # noqa: PLR0913
    table: Table,
    name: TableName,
    rules: TableDiscoveryRules,
    tables_repo: TablesRepo,
    table_change_gateway: SendTableChangeGateway,
    seen_change: TableChange | None,
    now: datetime,
    *,
    last_committed_at: datetime | None = None,
) -> KnownTableOutcome:
    """Apply one discovery of a known, live table: rename, decide, note its last commit and tell the runtime.

    The table is renamed when its name changed and decided again by the rules,
    and its last commit moves to ``last_committed_at`` when that is newer. A
    rename or a management change is stored in one full update (with the new
    deciding rule and the last commit); a table whose only change is a newer
    commit gets just that written, so this copy of the table, read before any
    other writer's change, never puts the rest of it back. A table
    the rules unmanage is sent ``stopped``; one they manage again is sent
    ``managed`` as a managed table, so its workflow starts again under the same ID
    and checks it at once. A table whose management did not change (a rule-only
    change included) is sent ``seen_change`` only when it is managed and
    ``seen_change`` is given.
    """
    renamed = table.name != name
    if renamed:
        table.rename(name, now)
    change = decide_table_management(table, rules, now)
    committed = table.record_last_commit(last_committed_at)
    if renamed or change != TableManagementChange.UNCHANGED:
        tables_repo.update(table)
    elif committed and last_committed_at is not None:
        tables_repo.record_last_commit(table.id, last_committed_at)
    signalled = False
    if change == TableManagementChange.UNMANAGED:
        _send(table_change_gateway, table, TableChange.STOPPED)
    elif change == TableManagementChange.MANAGED:
        _send(table_change_gateway, table, TableChange.MANAGED)
    elif table.is_managed and seen_change is not None:
        _send(table_change_gateway, table, seen_change)
        signalled = True
    return KnownTableOutcome(renamed=renamed, change=change, signalled=signalled)


def _send(gateway: SendTableChangeGateway, table: Table, change: TableChange) -> None:
    gateway.send(
        SendTableChangeGatewayInput(
            table_uuid=table.id.value,
            table_name=table.name.fully_qualified(),
            change=change.value,
            is_managed=table.is_managed,
        )
    )
