"""Test the ListTableCommitsService."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceSettings,
)
from context.table_maintenance.application.domain.model.table import (
    Table,
    TableId,
    TableName,
)
from context.table_maintenance.application.domain.model.table_discovery_rule import (
    TableDiscoveryRuleId,
)
from context.table_maintenance.application.domain.model.table_maintenance_preset import (
    TableMaintenancePresetId,
)
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table import (
    ListTableCommitsUseCaseInput,
)
from context.table_maintenance.application.port.outbound.table import (
    TableCommitPage,
    TableCommitSelection,
)
from context.table_maintenance.application.service.table import ListTableCommitsService

KEY = ("iceberg", "sales", "orders")


@pytest.fixture
def service(tables_repo, catalog, now):
    """Provide the list table commits service on the fakes."""
    tables_repo.create(
        Table.register_auto(
            TableId("u-1"),
            TableName(*KEY),
            TableDiscoveryRuleId("r-1"),
            TableMaintenancePresetId("t-1"),
            MaintenanceSettings(),
            now,
        )
    )
    return ListTableCommitsService(tables_repo, catalog)


def _commit(summary: dict[str, str], **overrides):
    commit = {
        "snapshot_id": 7,
        "parent_id": 6,
        "committed_at": "2026-10-24T12:00:00+00:00",
        "operation": "append",
        "summary": summary,
        "writer": "unknown",
    }
    commit.update(overrides)
    return commit


def test_commits_map_counters_and_writer(service, catalog):
    """A commit maps its ids, time, counters and writer from the snapshot."""
    summary = {
        "added-records": "10",
        "deleted-records": "2",
        "added-data-files": "3",
        "deleted-data-files": "1",
        "added-delete-files": "4",
        "removed-delete-files": "5",
    }
    catalog.commit_pages[KEY] = TableCommitPage(
        table_uuid="u-1", commits=[_commit(summary, writer="spark")], truncated=False
    )

    output = service.execute(ListTableCommitsUseCaseInput(uuid="u-1"))

    item = output.items[0]
    assert item.snapshot_id == 7
    assert item.parent_id == 6
    assert item.committed_at == datetime(2026, 10, 24, 12, 0, tzinfo=UTC)
    assert item.operation == "append"
    assert item.writer == "spark"
    assert item.added_records == 10
    assert item.deleted_records == 2
    assert item.added_data_files == 3
    assert item.deleted_data_files == 1
    assert item.added_delete_files == 4
    assert item.removed_delete_files == 5
    assert item.summary == summary
    assert output.truncated is False


def test_commit_with_partial_summary(service, catalog):
    """A commit with a partial summary reports None for the missing counters."""
    catalog.commit_pages[KEY] = TableCommitPage(
        table_uuid="u-1", commits=[_commit({"added-records": "abc"})], truncated=False
    )

    item = service.execute(ListTableCommitsUseCaseInput(uuid="u-1")).items[0]

    assert item.added_records is None
    assert item.deleted_records is None
    assert item.removed_delete_files is None


def test_truncated_passes_through(service, catalog):
    """The truncated flag of the catalog page is passed through."""
    catalog.commit_pages[KEY] = TableCommitPage(table_uuid="u-1", commits=[_commit({})], truncated=True)

    output = service.execute(ListTableCommitsUseCaseInput(uuid="u-1"))

    assert output.truncated is True


def test_limit_time_window_and_writer_are_forwarded(service, catalog):
    """The limit, the time window and the writer are forwarded to the catalog."""
    catalog.commit_pages[KEY] = TableCommitPage(table_uuid="u-1", commits=[], truncated=False)
    since = datetime(2026, 10, 1, tzinfo=UTC)
    before = datetime(2026, 10, 8, tzinfo=UTC)

    service.execute(ListTableCommitsUseCaseInput(uuid="u-1", limit=5, since=since, before=before, writer="spark"))

    name, (_, got) = catalog.calls[-1]
    assert name == "list_commits"
    assert got == TableCommitSelection(limit=5, since=since.isoformat(), before=before.isoformat(), writer="spark")


def test_commits_unknown_table_raises_not_found(service):
    """An unknown table raises NotFoundError."""
    with pytest.raises(NotFoundError, match="table u-9 not found"):
        service.execute(ListTableCommitsUseCaseInput(uuid="u-9"))


def test_commits_404_when_not_in_catalog(service):
    """A table missing from the catalog raises NotFoundError."""
    with pytest.raises(NotFoundError, match="is not in the catalog$"):
        service.execute(ListTableCommitsUseCaseInput(uuid="u-1"))


def test_commits_404_when_catalog_table_has_another_uuid(service, catalog):
    """A catalog table with a different uuid raises NotFoundError."""
    catalog.commit_pages[KEY] = TableCommitPage(table_uuid="u-recreated", commits=[_commit({})], truncated=False)

    with pytest.raises(NotFoundError, match="is not in the catalog$"):
        service.execute(ListTableCommitsUseCaseInput(uuid="u-1"))
