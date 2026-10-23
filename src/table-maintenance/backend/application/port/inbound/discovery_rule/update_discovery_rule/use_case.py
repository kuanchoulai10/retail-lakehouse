"""Define the UpdateDiscoveryRuleUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.discovery_rule.update_discovery_rule.input import (
    UpdateDiscoveryRuleUseCaseInput,
)
from application.port.inbound.discovery_rule.update_discovery_rule.output import (
    UpdateDiscoveryRuleUseCaseOutput,
)
from base.use_case import UseCase


class UpdateDiscoveryRuleUseCase(
    UseCase[UpdateDiscoveryRuleUseCaseInput, UpdateDiscoveryRuleUseCaseOutput]
):
    """Replace a discovery rule's definition."""

    @abstractmethod
    def execute(
        self, request: UpdateDiscoveryRuleUseCaseInput
    ) -> UpdateDiscoveryRuleUseCaseOutput:
        """Replace a discovery rule's definition."""
