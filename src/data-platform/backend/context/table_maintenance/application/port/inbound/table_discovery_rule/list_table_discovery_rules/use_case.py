"""Define the ListTableDiscoveryRulesUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_discovery_rule.list_table_discovery_rules.input import (
    ListTableDiscoveryRulesUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_rule.list_table_discovery_rules.output import (
    ListTableDiscoveryRulesUseCaseOutput,
)


class ListTableDiscoveryRulesUseCase(
    UseCase[ListTableDiscoveryRulesUseCaseInput, ListTableDiscoveryRulesUseCaseOutput]
):
    """List all discovery rules."""

    @abstractmethod
    def execute(self, request: ListTableDiscoveryRulesUseCaseInput) -> ListTableDiscoveryRulesUseCaseOutput:
        """List all discovery rules."""
