"""Define the GetTableDiscoveryRulesService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.port.inbound.table_discovery_rules import (
    GetTableDiscoveryRulesUseCase,
    GetTableDiscoveryRulesUseCaseInput,
    GetTableDiscoveryRulesUseCaseOutput,
    GetTableDiscoveryRulesUseCaseOutputItem,
)
from context.table_maintenance.application.service.table_discovery_rules.table_discovery_rule_output_fields import (
    table_discovery_rule_output_fields,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_discovery_rules import (
        TableDiscoveryRulesRepo,
    )


class GetTableDiscoveryRulesService(GetTableDiscoveryRulesUseCase):
    """Return the discovery rules in priority order with the list's version."""

    def __init__(self, rules_repo: TableDiscoveryRulesRepo) -> None:
        """Bind the repo."""
        self._rules_repo = rules_repo

    def execute(
        self,
        request: GetTableDiscoveryRulesUseCaseInput,  # noqa: ARG002
    ) -> GetTableDiscoveryRulesUseCaseOutput:
        """Return the stored rules; none at version 0 before the first save."""
        rules = self._rules_repo.get_rules()
        return GetTableDiscoveryRulesUseCaseOutput(
            version=rules.version,
            rules=[
                GetTableDiscoveryRulesUseCaseOutputItem(**table_discovery_rule_output_fields(r)) for r in rules.rules
            ],
        )
