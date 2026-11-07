"""Ask for an ad-hoc discovery of a catalog or namespace."""

from application.port.outbound.table.send_discovery_request.gateway import (
    SendDiscoveryRequestGateway,
)
from application.port.outbound.table.send_discovery_request.input import (
    SendDiscoveryRequestGatewayInput,
)

__all__ = [
    "SendDiscoveryRequestGateway",
    "SendDiscoveryRequestGatewayInput",
]
