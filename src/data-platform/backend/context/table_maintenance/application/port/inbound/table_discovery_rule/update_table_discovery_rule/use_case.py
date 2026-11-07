"""Define the UpdateTableDiscoveryRuleUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from context.table_maintenance.application.port.inbound.table_discovery_rule.update_table_discovery_rule.input import (
    UpdateTableDiscoveryRuleUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_rule.update_table_discovery_rule.output import (
    UpdateTableDiscoveryRuleUseCaseOutput,
)
from base import UseCase


class UpdateTableDiscoveryRuleUseCase(
    UseCase[UpdateTableDiscoveryRuleUseCaseInput, UpdateTableDiscoveryRuleUseCaseOutput]
):
    """Replace a discovery rule's definition."""

    @abstractmethod
    def execute(self, request: UpdateTableDiscoveryRuleUseCaseInput) -> UpdateTableDiscoveryRuleUseCaseOutput:
        """Replace a discovery rule's definition."""
