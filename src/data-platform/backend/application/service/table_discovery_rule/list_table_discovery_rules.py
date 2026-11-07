"""Define the ListTableDiscoveryRulesService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.inbound.table_discovery_rule import (
    ListTableDiscoveryRulesUseCase,
    ListTableDiscoveryRulesUseCaseInput,
    ListTableDiscoveryRulesUseCaseOutput,
    ListTableDiscoveryRulesUseCaseOutputItem,
)
from application.service.table_discovery_rule.table_discovery_rule_output_fields import (
    table_discovery_rule_output_fields,
)

if TYPE_CHECKING:
    from application.port.outbound.table_discovery_rule import TableDiscoveryRulesRepo


class ListTableDiscoveryRulesService(ListTableDiscoveryRulesUseCase):
    """List all discovery rules."""

    def __init__(self, rules_repo: TableDiscoveryRulesRepo) -> None:
        """Bind the repo."""
        self._rules_repo = rules_repo

    def execute(
        self,
        request: ListTableDiscoveryRulesUseCaseInput,  # noqa: ARG002
    ) -> ListTableDiscoveryRulesUseCaseOutput:
        """Return every rule in priority order."""
        return ListTableDiscoveryRulesUseCaseOutput(
            items=[
                ListTableDiscoveryRulesUseCaseOutputItem(
                    **table_discovery_rule_output_fields(r)
                )
                for r in self._rules_repo.list_all()
            ]
        )
