"""Define the TableDiscoveryActivities Temporal activities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from temporalio import activity

from context.table_maintenance.adapter.hybrid.temporal.inbound.activities.activity_payload import (
    activity_payload,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.activities.translate_application_errors import (
    translate_application_errors,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_discovery import (
    TableDiscoveryActivity,
)
from context.table_maintenance.application.port.inbound.table import (
    SyncDiscoveredTablesUseCaseInput,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.inbound.table import (
        SyncDiscoveredTablesUseCase,
    )


class TableDiscoveryActivities:
    """Synchronise the table registry with the catalog."""

    def __init__(self, *, sync: SyncDiscoveredTablesUseCase) -> None:
        """Bind the sync use case."""
        self._sync = sync

    @activity.defn(name=TableDiscoveryActivity.SYNC_DISCOVERED_TABLES)
    def sync_discovered_tables(self, request: dict[str, Any]) -> dict[str, Any]:
        """Synchronise the registry with one catalog or namespace."""
        with translate_application_errors():
            output = self._sync.execute(
                SyncDiscoveredTablesUseCaseInput(catalog=request["catalog"], namespace=request.get("namespace"))
            )
        return activity_payload(output)
