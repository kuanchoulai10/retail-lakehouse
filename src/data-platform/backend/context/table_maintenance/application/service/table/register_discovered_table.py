"""Define the register_discovered_table function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table import (
    Table,
    TableId,
    TableName,
)
from context.table_maintenance.application.domain.model.table_discovery_rules import (
    RuleAction,
)
from context.table_maintenance.application.port.outbound.table import (
    SendTableChangeGatewayInput,
)
from context.table_maintenance.application.service.table.registration_outcome import (
    RegistrationOutcome,
)

if TYPE_CHECKING:
    from datetime import datetime

    from context.table_maintenance.application.domain.model.table import TableChange
    from context.table_maintenance.application.domain.model.table_discovery_rules import (
        TableDiscoveryRules,
    )
    from context.table_maintenance.application.port.outbound.table import (
        SendTableChangeGateway,
        TableMetadata,
        TablesRepo,
    )


def register_discovered_table(  # noqa: PLR0913
    found: TableMetadata,
    rules: TableDiscoveryRules,
    tables_repo: TablesRepo,
    table_change_gateway: SendTableChangeGateway,
    change: TableChange,
    now: datetime,
) -> RegistrationOutcome:
    """Decide an unknown table by the discovery rules and register it.

    An include match registers the table as managed and sends ``change`` for it,
    which starts its reconciliation workflow. An exclude match, or no match,
    registers it as unmanaged and sends nothing, so the registry lists every
    table discovery has seen.
    """
    name = TableName(catalog=found.catalog, namespace=found.namespace, table=found.table)
    rule = rules.decide(name)
    if rule is None or rule.action != RuleAction.INCLUDE:
        tables_repo.create(Table.register_unmanaged(TableId(found.table_uuid), name, now))
        return RegistrationOutcome.UNMANAGED
    table = Table.register(TableId(found.table_uuid), name, rule.id, now)
    tables_repo.create(table)
    table_change_gateway.send(
        SendTableChangeGatewayInput(
            table_uuid=table.id.value,
            table_name=name.fully_qualified(),
            change=change.value,
            is_managed=table.is_managed,
        )
    )
    return RegistrationOutcome.MANAGED
