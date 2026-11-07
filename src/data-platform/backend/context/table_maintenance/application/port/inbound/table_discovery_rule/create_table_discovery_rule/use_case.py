"""Define the CreateTableDiscoveryRuleUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_discovery_rule.create_table_discovery_rule.input import (
    CreateTableDiscoveryRuleUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_rule.create_table_discovery_rule.output import (
    CreateTableDiscoveryRuleUseCaseOutput,
)


class CreateTableDiscoveryRuleUseCase(
    UseCase[CreateTableDiscoveryRuleUseCaseInput, CreateTableDiscoveryRuleUseCaseOutput]
):
    """Create a discovery rule."""

    @abstractmethod
    def execute(self, request: CreateTableDiscoveryRuleUseCaseInput) -> CreateTableDiscoveryRuleUseCaseOutput:
        """Create a discovery rule."""
