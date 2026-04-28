"""Define the UpdateTablePropertiesGateway port interface."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base.gateway import Gateway

if TYPE_CHECKING:
    from application.port.outbound.catalog.update_table_properties.input import (
        UpdateTablePropertiesGatewayInput,
    )


class UpdateTablePropertiesGateway(Gateway):
    """Gateway for updating Iceberg table properties via the catalog."""

    @abstractmethod
    def execute(self, input: UpdateTablePropertiesGatewayInput) -> None:
        """Set and/or remove table properties."""
        ...
