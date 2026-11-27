"""Define the SyncDiscoverySchedulesService."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.service.catalog_discovery import catalogs_to_scan
from context.table_maintenance.application.port.inbound.table_discovery_policy import (
    SyncDiscoverySchedulesUseCase,
    SyncDiscoverySchedulesUseCaseInput,
    SyncDiscoverySchedulesUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table import SendDiscoveryRequestGatewayInput
from context.table_maintenance.application.port.outbound.table_discovery_policy import (
    SyncDiscoverySchedulesGatewayInput,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from context.table_maintenance.application.port.outbound.shared import PolicyPlacementsStore
    from context.table_maintenance.application.port.outbound.table import SendDiscoveryRequestGateway, TablesRepo
    from context.table_maintenance.application.port.outbound.table_discovery_policy import (
        SyncDiscoverySchedulesGateway,
    )


class SyncDiscoverySchedulesService(SyncDiscoverySchedulesUseCase):
    """Bring the discovery schedules in line with the scanned catalogs, as the worker does at every start."""

    def __init__(
        self,
        placements: PolicyPlacementsStore,
        tables_repo: TablesRepo,
        discovery_requests: SendDiscoveryRequestGateway,
        schedules: SyncDiscoverySchedulesGateway,
        *,
        new_change_id: Callable[[], str] = lambda: uuid.uuid4().hex,
    ) -> None:
        """Bind the placements, the tables, the discovery requests, the schedules and the change id generator."""
        self._placements = placements
        self._tables_repo = tables_repo
        self._discovery_requests = discovery_requests
        self._schedules = schedules
        self._new_change_id = new_change_id

    def execute(self, request: SyncDiscoverySchedulesUseCaseInput) -> SyncDiscoverySchedulesUseCaseOutput:  # noqa: ARG002
        """Create the missing schedules, give each catalog that left its final scan, then delete its schedule.

        The scanned catalogs are ``catalogs_to_scan``'s: those where a discovery policy is attached and
        those still holding a managed table. A catalog that left has a schedule but neither any more.
        Every error propagates, and a final scan that cannot start deletes no schedule, so the next
        start tries again.
        """
        wanted = catalogs_to_scan(
            self._placements.catalogs_with_discovery_policy(), self._tables_repo.list_catalogs_with_managed_tables()
        )
        left = tuple(sorted(set(self._schedules.list_scheduled_catalogs()) - set(wanted)))
        if left:
            change_id = self._new_change_id()
            for catalog in left:
                self._discovery_requests.send(
                    SendDiscoveryRequestGatewayInput(catalog, None, change_id=change_id, retires_schedule=True)
                )
        self._schedules.sync(SyncDiscoverySchedulesGatewayInput(catalogs=wanted, removed=left))
        return SyncDiscoverySchedulesUseCaseOutput(catalogs=wanted)
