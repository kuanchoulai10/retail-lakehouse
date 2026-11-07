"""Define the Gateways bundle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table import (
        ReadTableMetadataGateway,
        SendDiscoveryRequestGateway,
        SendTableChangeGateway,
    )
    from context.table_maintenance.application.port.outbound.table_discovery_settings import (
        UpdateTableDiscoveryScheduleGateway,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_run import (
        DeleteMaintenanceJobGateway,
        ReadMaintenanceJobGateway,
        SubmitMaintenanceJobGateway,
        SendMaintenanceResultGateway,
    )


@dataclass(frozen=True)
class Gateways:
    """Hold one implementation of every outbound gateway port."""

    read_table_metadata: ReadTableMetadataGateway
    send_table_change: SendTableChangeGateway
    send_discovery_request: SendDiscoveryRequestGateway
    send_maintenance_result: SendMaintenanceResultGateway
    update_table_discovery_schedule: UpdateTableDiscoveryScheduleGateway
    submit_maintenance_job: SubmitMaintenanceJobGateway
    read_maintenance_job: ReadMaintenanceJobGateway
    delete_maintenance_job: DeleteMaintenanceJobGateway
