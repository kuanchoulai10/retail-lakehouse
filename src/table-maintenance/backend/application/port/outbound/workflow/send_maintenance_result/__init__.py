"""Send a maintenance result to the workflow."""

from application.port.outbound.workflow.send_maintenance_result.gateway import (
    SendMaintenanceResultGateway,
)
from application.port.outbound.workflow.send_maintenance_result.input import (
    SendMaintenanceResultGatewayInput,
)

__all__ = [
    "SendMaintenanceResultGateway",
    "SendMaintenanceResultGatewayInput",
]
