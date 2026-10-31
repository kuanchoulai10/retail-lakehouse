"""Define the ListTableCommitsService."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from application.port.inbound.table import (
    ListTableCommitsUseCase,
    ListTableCommitsUseCaseInput,
    ListTableCommitsUseCaseOutput,
    ListTableCommitsUseCaseOutputItem,
)
from application.service.table.load_catalog_table import load_catalog_table
from application.service.table.raise_not_in_catalog import raise_not_in_catalog
from application.service.table.summary_int import summary_int

if TYPE_CHECKING:
    from typing import Any

    from application.port.outbound.table import ReadTableMetadataGateway, TablesRepo


def _to_item(commit: dict[str, Any]) -> ListTableCommitsUseCaseOutputItem:
    summary = commit["summary"]
    return ListTableCommitsUseCaseOutputItem(
        snapshot_id=commit["snapshot_id"],
        parent_id=commit["parent_id"],
        committed_at=datetime.fromisoformat(commit["committed_at"]),
        operation=commit["operation"],
        writer=commit["writer"],
        added_records=summary_int(summary, "added-records"),
        deleted_records=summary_int(summary, "deleted-records"),
        added_data_files=summary_int(summary, "added-data-files"),
        deleted_data_files=summary_int(summary, "deleted-data-files"),
        added_delete_files=summary_int(summary, "added-delete-files"),
        removed_delete_files=summary_int(summary, "removed-delete-files"),
        summary=summary,
    )


class ListTableCommitsService(ListTableCommitsUseCase):
    """List the commits of a table from the catalog, newest first."""

    def __init__(
        self, tables_repo: TablesRepo, catalog_gateway: ReadTableMetadataGateway
    ) -> None:
        """Bind the repo and the catalog gateway."""
        self._tables_repo = tables_repo
        self._catalog_gateway = catalog_gateway

    def execute(
        self, request: ListTableCommitsUseCaseInput
    ) -> ListTableCommitsUseCaseOutput:
        """Return the commits or raise NotFoundError."""
        table, ref = load_catalog_table(self._tables_repo, request.uuid)
        since = None if request.since is None else request.since.isoformat()
        page = self._catalog_gateway.list_commits(ref, since, request.limit)
        if page is None:
            raise_not_in_catalog(table)
        return ListTableCommitsUseCaseOutput(
            items=[_to_item(commit) for commit in page.commits],
            truncated=page.truncated,
        )
