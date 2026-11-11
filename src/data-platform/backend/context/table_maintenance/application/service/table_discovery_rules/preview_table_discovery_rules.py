"""Define the PreviewTableDiscoveryRulesService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table import TableName
from context.table_maintenance.application.domain.model.table_discovery_rules import (
    RuleAction,
    TableDiscoveryRules,
)
from context.table_maintenance.application.port.inbound.table_discovery_rules import (
    PreviewTableDiscoveryRulesUseCase,
    PreviewTableDiscoveryRulesUseCaseInput,
    PreviewTableDiscoveryRulesUseCaseOutput,
    PreviewTableDiscoveryRulesUseCaseOutputItem,
)
from context.table_maintenance.application.port.outbound.table import (
    ReadTableMetadataGatewayListInput,
)
from context.table_maintenance.application.service.shared import translate_domain_errors
from context.table_maintenance.application.service.table_discovery_rules.table_discovery_rule_from_request import (
    table_discovery_rule_from_request,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from context.table_maintenance.application.port.outbound.table import (
        ReadTableMetadataGateway,
        TableMetadataRef,
    )


class PreviewTableDiscoveryRulesService(PreviewTableDiscoveryRulesUseCase):
    """Decide every table of the covered catalogs by a candidate rule list, writing nothing."""

    def __init__(
        self,
        catalog_gateway: ReadTableMetadataGateway,
        catalog_names: Sequence[str],
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the catalog gateway, the covered catalogs and the clock."""
        self._catalog_gateway = catalog_gateway
        self._catalog_names = tuple(catalog_names)
        self._clock = clock

    def execute(self, request: PreviewTableDiscoveryRulesUseCaseInput) -> PreviewTableDiscoveryRulesUseCaseOutput:
        """Return each table with the rule that would decide it and whether it would be managed.

        The candidate list is checked as a save would check it. A rule without an
        id is named ``#<index>`` by its position in the candidate list.
        """
        now = self._clock()
        rules = TableDiscoveryRules.empty()
        with translate_domain_errors():
            candidates = [
                table_discovery_rule_from_request(item, item.id or f"#{index}", now)
                for index, item in enumerate(request.rules)
            ]
            rules.replace(candidates, rules.version, now, new_ids={rule.id for rule in candidates})
        tables = [
            _decide(rules, ref)
            for catalog_name in self._catalog_names
            for ref in self._catalog_gateway.list_tables(ReadTableMetadataGatewayListInput(catalog_name, None))
        ]
        managed = sum(item.managed for item in tables)
        return PreviewTableDiscoveryRulesUseCaseOutput(tables=tables, managed=managed, unmanaged=len(tables) - managed)


def _decide(rules: TableDiscoveryRules, ref: TableMetadataRef) -> PreviewTableDiscoveryRulesUseCaseOutputItem:
    rule = rules.decide(TableName(catalog=ref.catalog, namespace=ref.namespace, table=ref.table))
    return PreviewTableDiscoveryRulesUseCaseOutputItem(
        catalog=ref.catalog,
        namespace=ref.namespace,
        table=ref.table,
        rule_id=None if rule is None else rule.id.value,
        managed=rule is not None and rule.action == RuleAction.INCLUDE,
    )
