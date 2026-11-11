"""Define the GetTableDiscoveryRulesUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_discovery_rules.get_table_discovery_rules.input import (
    GetTableDiscoveryRulesUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_rules.get_table_discovery_rules.output import (
    GetTableDiscoveryRulesUseCaseOutput,
)


class GetTableDiscoveryRulesUseCase(UseCase[GetTableDiscoveryRulesUseCaseInput, GetTableDiscoveryRulesUseCaseOutput]):
    """Return the discovery rules in priority order with the list's version."""

    @abstractmethod
    def execute(self, request: GetTableDiscoveryRulesUseCaseInput) -> GetTableDiscoveryRulesUseCaseOutput:
        """Return the discovery rules in priority order with the list's version."""
