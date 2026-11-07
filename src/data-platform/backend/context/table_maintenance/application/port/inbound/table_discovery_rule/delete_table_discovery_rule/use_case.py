"""Define the DeleteTableDiscoveryRuleUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_discovery_rule.delete_table_discovery_rule.input import (
    DeleteTableDiscoveryRuleUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_rule.delete_table_discovery_rule.output import (
    DeleteTableDiscoveryRuleUseCaseOutput,
)


class DeleteTableDiscoveryRuleUseCase(
    UseCase[DeleteTableDiscoveryRuleUseCaseInput, DeleteTableDiscoveryRuleUseCaseOutput]
):
    """Delete a discovery rule."""

    @abstractmethod
    def execute(self, request: DeleteTableDiscoveryRuleUseCaseInput) -> DeleteTableDiscoveryRuleUseCaseOutput:
        """Delete a discovery rule."""
