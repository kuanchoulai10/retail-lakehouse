"""Ask for an ad-hoc discovery of a catalog or namespace."""

from context.table_maintenance.application.port.outbound.table.send_discovery_request.gateway import (
    SendDiscoveryRequestGateway,
)
from context.table_maintenance.application.port.outbound.table.send_discovery_request.input import (
    SendDiscoveryRequestGatewayInput,
)

__all__ = [
    "SendDiscoveryRequestGateway",
    "SendDiscoveryRequestGatewayInput",
]
