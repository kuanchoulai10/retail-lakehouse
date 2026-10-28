"""Define the ListTableDiscoveryRulesUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.table_discovery_rule.list_table_discovery_rules.input import (
    ListTableDiscoveryRulesUseCaseInput,
)
from application.port.inbound.table_discovery_rule.list_table_discovery_rules.output import (
    ListTableDiscoveryRulesUseCaseOutput,
)
from base.use_case import UseCase


class ListTableDiscoveryRulesUseCase(
    UseCase[ListTableDiscoveryRulesUseCaseInput, ListTableDiscoveryRulesUseCaseOutput]
):
    """List all discovery rules."""

    @abstractmethod
    def execute(
        self, request: ListTableDiscoveryRulesUseCaseInput
    ) -> ListTableDiscoveryRulesUseCaseOutput:
        """List all discovery rules."""
