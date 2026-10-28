"""Define the TableDiscoveryActivities Temporal activities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from temporalio import activity

from adapter.inbound.temporal.activities.activity_payload import activity_payload
from adapter.inbound.temporal.activities.translate_application_errors import (
    translate_application_errors,
)
from adapter.temporal_contracts.activity_names import SYNC_DISCOVERED_TABLES
from application.port.inbound.table.sync_discovered_tables import (
    SyncDiscoveredTablesUseCaseInput,
)

if TYPE_CHECKING:
    from application.port.inbound.table.sync_discovered_tables import (
        SyncDiscoveredTablesUseCase,
    )


class TableDiscoveryActivities:
    """Synchronise the table registry with the catalog."""

    def __init__(self, *, sync: SyncDiscoveredTablesUseCase) -> None:
        """Bind the sync use case."""
        self._sync = sync

    @activity.defn(name=SYNC_DISCOVERED_TABLES)
    def sync_discovered_tables(self, request: dict[str, Any]) -> dict[str, Any]:
        """Synchronise the registry with one catalog or namespace."""
        with translate_application_errors():
            output = self._sync.execute(
                SyncDiscoveredTablesUseCaseInput(
                    catalog=request["catalog"], namespace=request.get("namespace")
                )
            )
        return activity_payload(output)
