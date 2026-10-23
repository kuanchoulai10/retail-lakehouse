"""Define the SendDiscoveryRequestGateway outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base.gateway import Gateway

if TYPE_CHECKING:
    from application.port.outbound.workflow.send_discovery_request.input import (
        SendDiscoveryRequestGatewayInput,
    )


class SendDiscoveryRequestGateway(Gateway):
    """Send a discovery request to the workflow."""

    @abstractmethod
    def send(self, input: SendDiscoveryRequestGatewayInput) -> None:  # noqa: A002
        """Ask the discovery workflow to scan a catalog or namespace."""
