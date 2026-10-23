"""Update the table discovery schedule."""

from application.port.outbound.discovery.update_discovery_schedule.gateway import (
    UpdateDiscoveryScheduleGateway,
)
from application.port.outbound.discovery.update_discovery_schedule.input import (
    UpdateDiscoveryScheduleGatewayInput,
)

__all__ = ["UpdateDiscoveryScheduleGateway", "UpdateDiscoveryScheduleGatewayInput"]
