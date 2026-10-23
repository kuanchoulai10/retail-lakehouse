"""Define the ReadCatalogGateway outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base.gateway import Gateway

if TYPE_CHECKING:
    from application.port.outbound.catalog.read_catalog.list_input import (
        ReadCatalogGatewayListInput,
    )
    from application.port.outbound.catalog.read_catalog.observation import (
        ReadCatalogGatewayObservation,
    )
    from application.port.outbound.catalog.read_catalog.table import (
        ReadCatalogGatewayTable,
    )
    from application.port.outbound.catalog.read_catalog.table_ref import (
        ReadCatalogGatewayTableRef,
    )


class ReadCatalogGateway(Gateway):
    """Read table identities and statistics from the Iceberg catalog."""

    @abstractmethod
    def list_tables(
        self,
        input: ReadCatalogGatewayListInput,  # noqa: A002
    ) -> list[ReadCatalogGatewayTableRef]:
        """List the tables of a catalog, optionally within one namespace."""

    @abstractmethod
    def load_table(
        self, ref: ReadCatalogGatewayTableRef
    ) -> ReadCatalogGatewayTable | None:
        """Return the table with its uuid, or None when it does not exist."""

    @abstractmethod
    def observe_table(
        self, ref: ReadCatalogGatewayTableRef
    ) -> ReadCatalogGatewayObservation | None:
        """Return the table's statistics, or None when it does not exist."""
