"""Define the DeleteDiscoveryRuleUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.discovery_rule.delete_discovery_rule.input import (
    DeleteDiscoveryRuleUseCaseInput,
)
from application.port.inbound.discovery_rule.delete_discovery_rule.output import (
    DeleteDiscoveryRuleUseCaseOutput,
)
from base.use_case import UseCase


class DeleteDiscoveryRuleUseCase(
    UseCase[DeleteDiscoveryRuleUseCaseInput, DeleteDiscoveryRuleUseCaseOutput]
):
    """Delete a discovery rule."""

    @abstractmethod
    def execute(
        self, request: DeleteDiscoveryRuleUseCaseInput
    ) -> DeleteDiscoveryRuleUseCaseOutput:
        """Delete a discovery rule."""
