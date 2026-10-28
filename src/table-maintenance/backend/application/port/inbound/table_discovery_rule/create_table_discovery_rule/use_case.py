"""Define the CreateTableDiscoveryRuleUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.table_discovery_rule.create_table_discovery_rule.input import (
    CreateTableDiscoveryRuleUseCaseInput,
)
from application.port.inbound.table_discovery_rule.create_table_discovery_rule.output import (
    CreateTableDiscoveryRuleUseCaseOutput,
)
from base.use_case import UseCase


class CreateTableDiscoveryRuleUseCase(
    UseCase[CreateTableDiscoveryRuleUseCaseInput, CreateTableDiscoveryRuleUseCaseOutput]
):
    """Create a discovery rule."""

    @abstractmethod
    def execute(
        self, request: CreateTableDiscoveryRuleUseCaseInput
    ) -> CreateTableDiscoveryRuleUseCaseOutput:
        """Create a discovery rule."""
