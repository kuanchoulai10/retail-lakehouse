"""Update the table discovery schedule."""

from context.table_maintenance.application.port.outbound.table_discovery_settings.update_table_discovery_schedule.gateway import (  # noqa: E501
    UpdateTableDiscoveryScheduleGateway,
)
from context.table_maintenance.application.port.outbound.table_discovery_settings.update_table_discovery_schedule.input import (  # noqa: E501
    UpdateTableDiscoveryScheduleGatewayInput,
)

__all__ = [
    "UpdateTableDiscoveryScheduleGateway",
    "UpdateTableDiscoveryScheduleGatewayInput",
]
