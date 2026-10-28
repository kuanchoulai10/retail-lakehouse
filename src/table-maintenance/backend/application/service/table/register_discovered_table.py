"""Define the register_discovered_table function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.table.table import Table
from application.domain.model.table.table_name import TableName
from application.domain.model.table.table_id import TableId
from application.domain.model.shared.workflow_ids import SIGNAL_RESUME
from application.domain.model.table_discovery_rule.rule_effect import RuleEffect
from application.domain.service.table_discovery_rule.match_table_discovery_rule import (
    match_table_discovery_rule,
)
from application.port.outbound.workflow.send_table_signal import (
    SendTableSignalGatewayInput,
)
from application.service.table.registration_outcome import RegistrationOutcome

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from application.domain.model.table_discovery_rule.table_discovery_rule import (
        TableDiscoveryRule,
    )
    from application.port.outbound.table.read_table_metadata import TableMetadata
    from application.port.outbound.table.tables_repo import (
        TablesRepo,
    )
    from application.port.outbound.table_maintenance_preset.table_maintenance_presets_repo import (
        TableMaintenancePresetsRepo,
    )
    from application.port.outbound.workflow.send_table_signal import (
        SendTableSignalGateway,
    )


def register_discovered_table(  # noqa: PLR0913
    found: TableMetadata,
    rules: Sequence[TableDiscoveryRule],
    tables_repo: TablesRepo,
    presets_repo: TableMaintenancePresetsRepo,
    signal_gateway: SendTableSignalGateway,
    now: datetime,
) -> RegistrationOutcome:
    """Decide an unknown table by the discovery rules and register it if included.

    An INCLUDE match registers the table as AUTO ACTIVE with a copy of the rule's
    preset settings and starts its reconciliation workflow. An EXCLUDE match, or no
    match, registers nothing. A rule whose preset is missing is SKIPPED.
    """
    name = TableName(found.catalog, found.namespace, found.table)
    rule = match_table_discovery_rule(rules, name)
    if rule is None or rule.effect != RuleEffect.INCLUDE or rule.preset_id is None:
        return RegistrationOutcome.NOT_SELECTED
    preset = presets_repo.get(rule.preset_id)
    if preset is None:
        return RegistrationOutcome.SKIPPED
    uuid = TableId(found.table_uuid)
    tables_repo.create(
        Table.register_auto(uuid, name, rule.id, preset.id, preset.settings, now)
    )
    signal_gateway.send(
        SendTableSignalGatewayInput(
            table_uuid=uuid.value,
            table_name=name.fully_qualified(),
            signal=SIGNAL_RESUME,
            start_if_missing=True,
        )
    )
    return RegistrationOutcome.REGISTERED
