"""Define the SendDiscoveryRequestGateway outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base import Gateway

if TYPE_CHECKING:
    from application.port.outbound.table.send_discovery_request.input import (
        SendDiscoveryRequestGatewayInput,
    )


class SendDiscoveryRequestGateway(Gateway):
    """Ask for an ad-hoc discovery of a catalog or namespace."""

    @abstractmethod
    def send(self, input: SendDiscoveryRequestGatewayInput) -> None:  # noqa: A002
        """Ask for the catalog or namespace to be scanned for tables."""
