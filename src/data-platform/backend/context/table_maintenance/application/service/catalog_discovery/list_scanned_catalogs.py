"""Define the ListScannedCatalogsService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.service.catalog_discovery import catalogs_to_scan
from context.table_maintenance.application.port.inbound.catalog_discovery import (
    ListScannedCatalogsUseCase,
    ListScannedCatalogsUseCaseInput,
    ListScannedCatalogsUseCaseOutput,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.catalog_discovery import (
        CatalogDiscoveriesRepo,
        CatalogDiscovery,
    )
    from context.table_maintenance.application.port.outbound.shared import PolicyPlacementsStore
    from context.table_maintenance.application.port.outbound.table import TablesRepo


class ListScannedCatalogsService(ListScannedCatalogsUseCase):
    """List the catalogs discovery scans, with each one's scan state."""

    def __init__(
        self,
        placements: PolicyPlacementsStore,
        tables_repo: TablesRepo,
        discoveries_repo: CatalogDiscoveriesRepo,
    ) -> None:
        """Bind the placements, the tables and the catalog discoveries."""
        self._placements = placements
        self._tables_repo = tables_repo
        self._discoveries_repo = discoveries_repo

    def execute(self, request: ListScannedCatalogsUseCaseInput) -> ListScannedCatalogsUseCaseOutput:  # noqa: ARG002
        """Return each scanned catalog by name, with its last completed scan and its current failure.

        The scanned catalogs are ``catalogs_to_scan``'s: each where a discovery policy is attached (to
        the catalog, a namespace or a table of it) and each still holding a managed table. A catalog
        not yet scanned has neither scan state. A catalog's record outlives its scanning: a catalog
        that is not scanned any more is not listed, whatever it recorded.
        """
        scanned = catalogs_to_scan(
            self._placements.catalogs_with_discovery_policy(), self._tables_repo.list_catalogs_with_managed_tables()
        )
        discoveries = {d.catalog: d for d in self._discoveries_repo.list_all()}
        return ListScannedCatalogsUseCaseOutput(
            catalogs=tuple(_scanned_catalog(catalog, discoveries.get(catalog)) for catalog in scanned)
        )


def _scanned_catalog(
    catalog: str, discovery: CatalogDiscovery | None
) -> ListScannedCatalogsUseCaseOutput.ScannedCatalog:
    if discovery is None:
        return ListScannedCatalogsUseCaseOutput.ScannedCatalog(catalog=catalog, last_discovered_at=None, failure=None)
    failure = discovery.current_failure
    return ListScannedCatalogsUseCaseOutput.ScannedCatalog(
        catalog=catalog,
        last_discovered_at=discovery.last_discovered_at,
        failure=None
        if failure is None
        else ListScannedCatalogsUseCaseOutput.Failure(
            reason=failure.reason.value, detail=failure.detail, failed_at=failure.failed_at
        ),
    )
