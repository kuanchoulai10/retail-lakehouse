"""Define the DeleteTableDiscoveryRuleUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.table_discovery_rule.delete_table_discovery_rule.input import (
    DeleteTableDiscoveryRuleUseCaseInput,
)
from application.port.inbound.table_discovery_rule.delete_table_discovery_rule.output import (
    DeleteTableDiscoveryRuleUseCaseOutput,
)
from base import UseCase


class DeleteTableDiscoveryRuleUseCase(
    UseCase[DeleteTableDiscoveryRuleUseCaseInput, DeleteTableDiscoveryRuleUseCaseOutput]
):
    """Delete a discovery rule."""

    @abstractmethod
    def execute(
        self, request: DeleteTableDiscoveryRuleUseCaseInput
    ) -> DeleteTableDiscoveryRuleUseCaseOutput:
        """Delete a discovery rule."""
