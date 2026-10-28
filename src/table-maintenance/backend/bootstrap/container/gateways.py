"""Define the Gateways bundle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from application.port.outbound.table.read_table_metadata import (
        ReadTableMetadataGateway,
    )
    from application.port.outbound.table_discovery_settings.update_table_discovery_schedule import (
        UpdateTableDiscoveryScheduleGateway,
    )
    from application.port.outbound.table_maintenance_run.delete_maintenance_job import (
        DeleteMaintenanceJobGateway,
    )
    from application.port.outbound.table_maintenance_run.read_maintenance_job import (
        ReadMaintenanceJobGateway,
    )
    from application.port.outbound.table_maintenance_run.submit_maintenance_job import (
        SubmitMaintenanceJobGateway,
    )
    from application.port.outbound.table.send_discovery_request import (
        SendDiscoveryRequestGateway,
    )
    from application.port.outbound.table_maintenance_run.send_maintenance_result import (
        SendMaintenanceResultGateway,
    )
    from application.port.outbound.table.send_table_change import (
        SendTableChangeGateway,
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
