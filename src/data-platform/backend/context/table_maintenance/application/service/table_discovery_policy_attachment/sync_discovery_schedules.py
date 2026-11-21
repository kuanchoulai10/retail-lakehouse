"""Define the SyncDiscoverySchedulesService."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from context.table_maintenance.application.port.inbound.table_discovery_policy_attachment import (
    SyncDiscoverySchedulesUseCase,
    SyncDiscoverySchedulesUseCaseInput,
    SyncDiscoverySchedulesUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table import SendDiscoveryRequestGatewayInput
from context.table_maintenance.application.port.outbound.table_discovery_policy_attachment import (
    SyncDiscoverySchedulesGatewayInput,
)
from context.table_maintenance.application.service.table_discovery_policy_attachment.read_scanned_catalogs import (
    read_scanned_catalogs,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from context.table_maintenance.application.port.outbound.table import SendDiscoveryRequestGateway
    from context.table_maintenance.application.port.outbound.table_discovery_policy import (
        TableDiscoveryPoliciesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_discovery_policy_attachment import (
        SyncDiscoverySchedulesGateway,
        TableDiscoveryPolicyAttachmentsRepo,
    )


class SyncDiscoverySchedulesService(SyncDiscoverySchedulesUseCase):
    """Bring the discovery schedules in line with the scanned catalogs, as the worker does at every start."""

    def __init__(
        self,
        policies_repo: TableDiscoveryPoliciesRepo,
        attachments_repo: TableDiscoveryPolicyAttachmentsRepo,
        discovery_requests: SendDiscoveryRequestGateway,
        schedules: SyncDiscoverySchedulesGateway,
        *,
        new_change_id: Callable[[], str] = lambda: uuid.uuid4().hex,
    ) -> None:
        """Bind the repos, the discovery requests, the schedules and the change id generator."""
        self._policies_repo = policies_repo
        self._attachments_repo = attachments_repo
        self._discovery_requests = discovery_requests
        self._schedules = schedules
        self._new_change_id = new_change_id

    def execute(self, request: SyncDiscoverySchedulesUseCaseInput) -> SyncDiscoverySchedulesUseCaseOutput:  # noqa: ARG002
        """Create the missing schedules, give each catalog that left its final scan, then delete its schedule.

        A catalog that left is one with a schedule that is no longer scanned: a change could not finish
        retiring it, or two changes raced. Its final scan unmanages its tables. Every error propagates,
        and a final scan that cannot start deletes no schedule, so the next start tries again.
        """
        wanted = read_scanned_catalogs(self._policies_repo, self._attachments_repo)
        left = tuple(sorted(set(self._schedules.list_scheduled_catalogs()) - set(wanted)))
        if left:
            change_id = self._new_change_id()
            for catalog in left:
                self._discovery_requests.send(SendDiscoveryRequestGatewayInput(catalog, None, change_id=change_id))
        self._schedules.sync(SyncDiscoverySchedulesGatewayInput(catalogs=wanted, removed=left))
        return SyncDiscoverySchedulesUseCaseOutput(catalogs=wanted)
