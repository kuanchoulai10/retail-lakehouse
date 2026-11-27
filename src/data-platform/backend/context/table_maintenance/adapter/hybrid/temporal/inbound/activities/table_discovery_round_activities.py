"""Define the TableDiscoveryRoundActivities Temporal activities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from temporalio import activity

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_discovery_round import (
    TableDiscoveryRoundActivity,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.activities.translate_application_errors import (
    translate_application_errors,
)
from context.table_maintenance.application.port.inbound.catalog_discovery import (
    ListScannedCatalogsUseCaseInput,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.inbound.catalog_discovery import (
        ListScannedCatalogsUseCase,
    )


class TableDiscoveryRoundActivities:
    """Tell a discovery round which catalogs to scan."""

    def __init__(self, *, list_scanned: ListScannedCatalogsUseCase) -> None:
        """Bind the use case that lists the scanned catalogs."""
        self._list_scanned = list_scanned

    @activity.defn(name=TableDiscoveryRoundActivity.LIST_SCANNED_CATALOGS)
    def list_scanned_catalogs(self) -> list[str]:
        """Return the names of the catalogs to scan, in the order the use case lists them."""
        with translate_application_errors():
            output = self._list_scanned.execute(ListScannedCatalogsUseCaseInput())
        return [scanned.catalog for scanned in output.catalogs]
