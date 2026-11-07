"""Define the SendTableChangeGateway outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base import Gateway

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table.send_table_change.input import (
        SendTableChangeGatewayInput,
    )


class SendTableChangeGateway(Gateway):
    """Tell whatever keeps a table maintained that the table changed."""

    @abstractmethod
    def send(self, input: SendTableChangeGatewayInput) -> None:  # noqa: A002
        """Deliver the change; an enrolled table is brought under maintenance first."""
