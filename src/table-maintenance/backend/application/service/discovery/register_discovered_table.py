"""Define the register_discovered_table function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.managed_table.managed_table import ManagedTable
from application.domain.model.managed_table.table_name import TableName
from application.domain.model.managed_table.table_uuid import TableUuid
from application.domain.model.maintenance.workflow_ids import SIGNAL_RESUME
from application.domain.model.discovery_rule.rule_effect import RuleEffect
from application.domain.service.match_discovery_rule import match_discovery_rule
from application.port.outbound.workflow.send_table_signal import (
    SendTableSignalGatewayInput,
)
from application.service.discovery.registration_outcome import RegistrationOutcome

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from application.domain.model.discovery_rule.discovery_rule import DiscoveryRule
    from application.port.outbound.catalog.read_catalog import ReadCatalogGatewayTable
    from application.port.outbound.managed_table.managed_tables_repo import (
        ManagedTablesRepo,
    )
    from application.port.outbound.policy_template.policy_templates_repo import (
        PolicyTemplatesRepo,
    )
    from application.port.outbound.workflow.send_table_signal import (
        SendTableSignalGateway,
    )


def register_discovered_table(  # noqa: PLR0913
    found: ReadCatalogGatewayTable,
    rules: Sequence[DiscoveryRule],
    tables_repo: ManagedTablesRepo,
    templates_repo: PolicyTemplatesRepo,
    signal_gateway: SendTableSignalGateway,
    now: datetime,
) -> RegistrationOutcome:
    """Decide an unknown table by the discovery rules and register it if included.

    An INCLUDE match registers the table as AUTO ACTIVE with a copy of the rule's
    template settings and starts its reconcile workflow. An EXCLUDE match, or no
    match, registers nothing. A rule whose template is missing is SKIPPED.
    """
    name = TableName(found.catalog, found.namespace, found.table)
    rule = match_discovery_rule(rules, name)
    if rule is None or rule.effect != RuleEffect.INCLUDE or rule.template_id is None:
        return RegistrationOutcome.NOT_SELECTED
    template = templates_repo.get(rule.template_id)
    if template is None:
        return RegistrationOutcome.SKIPPED
    uuid = TableUuid(found.table_uuid)
    tables_repo.create(
        ManagedTable.register_auto(
            uuid, name, rule.id, template.id, template.settings, now
        )
    )
    signal_gateway.send(
        SendTableSignalGatewayInput(
            table_uuid=uuid.value, signal=SIGNAL_RESUME, start_if_missing=True
        )
    )
    return RegistrationOutcome.REGISTERED
