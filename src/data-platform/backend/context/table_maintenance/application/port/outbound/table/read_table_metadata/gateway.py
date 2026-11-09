"""Define the ReadTableMetadataGateway outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base import Gateway

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table.read_table_metadata.list_input import (
        ReadTableMetadataGatewayListInput,
    )
    from context.table_maintenance.application.port.outbound.table.read_table_metadata.table_commit_page import (
        TableCommitPage,
    )
    from context.table_maintenance.application.port.outbound.table.read_table_metadata.table_commit_selection import (
        TableCommitSelection,
    )
    from context.table_maintenance.application.port.outbound.table.read_table_metadata.table_metadata import (
        TableMetadata,
    )
    from context.table_maintenance.application.port.outbound.table.read_table_metadata.table_metadata_observation import (  # noqa: E501
        TableMetadataObservation,
    )
    from context.table_maintenance.application.port.outbound.table.read_table_metadata.table_metadata_ref import (
        TableMetadataRef,
    )
    from context.table_maintenance.application.port.outbound.table.read_table_metadata.table_storage_measure import (
        TableStorageMeasure,
    )


class ReadTableMetadataGateway(Gateway):
    """Read table identities and statistics from the Iceberg catalog."""

    @abstractmethod
    def list_tables(
        self,
        input: ReadTableMetadataGatewayListInput,  # noqa: A002
    ) -> list[TableMetadataRef]:
        """List the tables of a catalog, optionally within one namespace."""

    @abstractmethod
    def load_table(self, ref: TableMetadataRef) -> TableMetadata | None:
        """Return the table with its uuid, or None when it does not exist."""

    @abstractmethod
    def observe_table(self, ref: TableMetadataRef) -> TableMetadataObservation | None:
        """Return the table's statistics, or None when it does not exist."""

    @abstractmethod
    def list_commits(
        self,
        ref: TableMetadataRef,
        selection: TableCommitSelection,
    ) -> TableCommitPage | None:
        """Return up to ``selection.limit`` of the commits ``selection`` keeps, newest first.

        None when the table does not exist.
        """

    @abstractmethod
    def measure_storage(self, ref: TableMetadataRef) -> TableStorageMeasure | None:
        """Return the table's current and referenced storage, or None."""
