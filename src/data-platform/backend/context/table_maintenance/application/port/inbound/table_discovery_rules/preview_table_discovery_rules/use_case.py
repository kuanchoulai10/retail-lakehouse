"""Define the PreviewTableDiscoveryRulesUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_discovery_rules.preview_table_discovery_rules.input import (  # noqa: E501
    PreviewTableDiscoveryRulesUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_rules.preview_table_discovery_rules.output import (  # noqa: E501
    PreviewTableDiscoveryRulesUseCaseOutput,
)


class PreviewTableDiscoveryRulesUseCase(
    UseCase[PreviewTableDiscoveryRulesUseCaseInput, PreviewTableDiscoveryRulesUseCaseOutput]
):
    """Preview which tables of the covered catalogs a candidate rule list would manage."""

    @abstractmethod
    def execute(self, request: PreviewTableDiscoveryRulesUseCaseInput) -> PreviewTableDiscoveryRulesUseCaseOutput:
        """Preview which tables of the covered catalogs a candidate rule list would manage."""
