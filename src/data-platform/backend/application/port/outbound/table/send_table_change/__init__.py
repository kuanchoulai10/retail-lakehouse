"""Tell the maintenance runtime that something changed about a table."""

from application.port.outbound.table.send_table_change.gateway import (
    SendTableChangeGateway,
)
from application.port.outbound.table.send_table_change.input import (
    SendTableChangeGatewayInput,
)

__all__ = ["SendTableChangeGateway", "SendTableChangeGatewayInput"]
