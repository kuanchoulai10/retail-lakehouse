"""Define the ListScannedCatalogsUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.catalog_discovery.list_scanned_catalogs.input import (
    ListScannedCatalogsUseCaseInput,
)
from context.table_maintenance.application.port.inbound.catalog_discovery.list_scanned_catalogs.output import (
    ListScannedCatalogsUseCaseOutput,
)


class ListScannedCatalogsUseCase(UseCase[ListScannedCatalogsUseCaseInput, ListScannedCatalogsUseCaseOutput]):
    """List the catalogs discovery scans, with each one's last scan and current failure."""

    @abstractmethod
    def execute(self, request: ListScannedCatalogsUseCaseInput) -> ListScannedCatalogsUseCaseOutput:
        """List the catalogs discovery scans, with each one's last scan and current failure."""
