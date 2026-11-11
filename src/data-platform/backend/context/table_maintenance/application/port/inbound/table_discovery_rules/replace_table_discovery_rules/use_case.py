"""Define the ReplaceTableDiscoveryRulesUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_discovery_rules.replace_table_discovery_rules.input import (  # noqa: E501
    ReplaceTableDiscoveryRulesUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_rules.replace_table_discovery_rules.output import (  # noqa: E501
    ReplaceTableDiscoveryRulesUseCaseOutput,
)


class ReplaceTableDiscoveryRulesUseCase(
    UseCase[ReplaceTableDiscoveryRulesUseCaseInput, ReplaceTableDiscoveryRulesUseCaseOutput]
):
    """Replace the whole discovery rule list from the version read, then discover tables."""

    @abstractmethod
    def execute(self, request: ReplaceTableDiscoveryRulesUseCaseInput) -> ReplaceTableDiscoveryRulesUseCaseOutput:
        """Replace the whole discovery rule list from the version read, then discover tables."""
