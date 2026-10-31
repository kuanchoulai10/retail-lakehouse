"""Define the GetTableMetadataService."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from application.port.inbound.table import (
    GetTableMetadataUseCase,
    GetTableMetadataUseCaseInput,
    GetTableMetadataUseCaseOutput,
)
from application.service.table.load_catalog_table import load_catalog_table
from application.service.table.raise_not_in_catalog import raise_not_in_catalog

if TYPE_CHECKING:
    from application.port.outbound.table import ReadTableMetadataGateway, TablesRepo


def _summary_int(summary: dict[str, str], key: str) -> int | None:
    try:
        return int(summary[key])
    except KeyError, ValueError:
        return None


class GetTableMetadataService(GetTableMetadataUseCase):
    """Describe a table's definition and current totals from the catalog."""

    def __init__(
        self, tables_repo: TablesRepo, catalog_gateway: ReadTableMetadataGateway
    ) -> None:
        """Bind the repo and the catalog gateway."""
        self._tables_repo = tables_repo
        self._catalog_gateway = catalog_gateway

    def execute(
        self, request: GetTableMetadataUseCaseInput
    ) -> GetTableMetadataUseCaseOutput:
        """Return the catalog metadata or raise NotFoundError."""
        table, ref = load_catalog_table(self._tables_repo, request.uuid)
        description = self._catalog_gateway.describe_table(ref)
        if description is None:
            raise_not_in_catalog(table)
        summary = description.current_summary
        committed = description.last_committed_at
        return GetTableMetadataUseCaseOutput(
            uuid=request.uuid,
            format_version=description.format_version,
            location=description.location,
            properties=description.properties,
            schema_fields=description.schema_fields,
            specs=description.specs,
            current_snapshot_id=description.current_snapshot_id,
            snapshot_count=description.snapshot_count,
            last_committed_at=(
                None if committed is None else datetime.fromisoformat(committed)
            ),
            total_records=_summary_int(summary, "total-records"),
            total_data_files=_summary_int(summary, "total-data-files"),
            total_delete_files=_summary_int(summary, "total-delete-files"),
            total_files_size_bytes=_summary_int(summary, "total-files-size"),
        )
