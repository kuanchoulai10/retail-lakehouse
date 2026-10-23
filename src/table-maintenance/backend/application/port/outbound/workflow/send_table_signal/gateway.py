"""Define the SendTableSignalGateway outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base.gateway import Gateway

if TYPE_CHECKING:
    from application.port.outbound.workflow.send_table_signal.input import (
        SendTableSignalGatewayInput,
    )


class SendTableSignalGateway(Gateway):
    """Signal the reconcile workflow of a table."""

    @abstractmethod
    def send(self, input: SendTableSignalGatewayInput) -> None:  # noqa: A002
        """Send the signal, starting the workflow first when asked to."""
