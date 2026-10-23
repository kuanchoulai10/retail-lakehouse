"""Define the CreateDiscoveryRuleUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.discovery_rule.create_discovery_rule.input import (
    CreateDiscoveryRuleUseCaseInput,
)
from application.port.inbound.discovery_rule.create_discovery_rule.output import (
    CreateDiscoveryRuleUseCaseOutput,
)
from base.use_case import UseCase


class CreateDiscoveryRuleUseCase(
    UseCase[CreateDiscoveryRuleUseCaseInput, CreateDiscoveryRuleUseCaseOutput]
):
    """Create a discovery rule."""

    @abstractmethod
    def execute(
        self, request: CreateDiscoveryRuleUseCaseInput
    ) -> CreateDiscoveryRuleUseCaseOutput:
        """Create a discovery rule."""
