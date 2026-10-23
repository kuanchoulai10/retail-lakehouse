"""Define the ListDiscoveryRulesUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.discovery_rule.list_discovery_rules.input import (
    ListDiscoveryRulesUseCaseInput,
)
from application.port.inbound.discovery_rule.list_discovery_rules.output import (
    ListDiscoveryRulesUseCaseOutput,
)
from base.use_case import UseCase


class ListDiscoveryRulesUseCase(
    UseCase[ListDiscoveryRulesUseCaseInput, ListDiscoveryRulesUseCaseOutput]
):
    """List all discovery rules."""

    @abstractmethod
    def execute(
        self, request: ListDiscoveryRulesUseCaseInput
    ) -> ListDiscoveryRulesUseCaseOutput:
        """List all discovery rules."""
