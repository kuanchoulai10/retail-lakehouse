"""Define POLARIS_CONNECTION_TYPES: the Polaris ``connectionType`` of each ConnectionType."""

from __future__ import annotations

from context.catalog.application.port.outbound.catalog import ConnectionType

POLARIS_CONNECTION_TYPES: dict[ConnectionType, str] = {
    ConnectionType.REST: "ICEBERG_REST",
    ConnectionType.HADOOP: "HADOOP",
    ConnectionType.HIVE: "HIVE",
}
