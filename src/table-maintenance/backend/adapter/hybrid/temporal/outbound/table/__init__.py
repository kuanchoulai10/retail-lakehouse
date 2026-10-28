"""Temporal-backed gateways of the table aggregate."""

from adapter.hybrid.temporal.outbound.table.send_discovery_request_temporal_gateway import (
    SendDiscoveryRequestTemporalGateway,
)
from adapter.hybrid.temporal.outbound.table.send_table_change_temporal_gateway import (
    SendTableChangeTemporalGateway,
)

__all__ = [
    "SendDiscoveryRequestTemporalGateway",
    "SendTableChangeTemporalGateway",
]
