"""Define the ListCoveredCatalogsUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_discovery_settings.list_covered_catalogs.input import (
    ListCoveredCatalogsUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_settings.list_covered_catalogs.output import (
    ListCoveredCatalogsUseCaseOutput,
)


class ListCoveredCatalogsUseCase(UseCase[ListCoveredCatalogsUseCaseInput, ListCoveredCatalogsUseCaseOutput]):
    """List the catalogs maintenance covers."""

    @abstractmethod
    def execute(self, request: ListCoveredCatalogsUseCaseInput) -> ListCoveredCatalogsUseCaseOutput:
        """List the catalogs maintenance covers."""
