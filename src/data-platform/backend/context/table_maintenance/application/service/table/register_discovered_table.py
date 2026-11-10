"""Define the register_discovered_table function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table import (
    Table,
    TableChange,
    TableId,
    TableName,
)
from context.table_maintenance.application.domain.model.table_discovery_rule import (
    RuleEffect,
)
from context.table_maintenance.application.domain.service.table_discovery_rule import (
    match_table_discovery_rule,
)
from context.table_maintenance.application.port.outbound.table import (
    SendTableChangeGatewayInput,
)
from context.table_maintenance.application.service.table.registration_outcome import (
    RegistrationOutcome,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from context.table_maintenance.application.domain.model.table_discovery_rule import (
        TableDiscoveryRule,
    )
    from context.table_maintenance.application.port.outbound.table import (
        SendTableChangeGateway,
        TableMetadata,
        TablesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_preset import (
        TableMaintenancePresetsRepo,
    )


def register_discovered_table(  # noqa: PLR0913
    found: TableMetadata,
    rules: Sequence[TableDiscoveryRule],
    tables_repo: TablesRepo,
    presets_repo: TableMaintenancePresetsRepo,
    table_change_gateway: SendTableChangeGateway,
    now: datetime,
) -> RegistrationOutcome:
    """Decide an unknown table by the discovery rules and register it if included.

    An INCLUDE match registers the table as AUTO ACTIVE with a copy of the rule's
    preset settings and starts its reconciliation workflow. An EXCLUDE match, or no
    match, registers nothing. A rule whose preset is missing is SKIPPED.
    """
    name = TableName(catalog=found.catalog, namespace=found.namespace, table=found.table)
    rule = match_table_discovery_rule(rules, name)
    if rule is None or rule.effect != RuleEffect.INCLUDE or rule.preset_id is None:
        return RegistrationOutcome.NOT_SELECTED
    preset = presets_repo.get(rule.preset_id)
    if preset is None:
        return RegistrationOutcome.SKIPPED
    uuid = TableId(found.table_uuid)
    table = Table.register_auto(uuid, name, rule.id, preset.id, preset.settings, now)
    tables_repo.create(table)
    table_change_gateway.send(
        SendTableChangeGatewayInput(
            table_uuid=uuid.value,
            table_name=name.fully_qualified(),
            change=TableChange.RESUMED.value,
            is_enrolled=table.is_enrolled,
        )
    )
    return RegistrationOutcome.REGISTERED
