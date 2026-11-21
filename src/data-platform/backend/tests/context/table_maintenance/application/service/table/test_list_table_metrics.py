"""Test the ListTableMetricsService."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.table import (
    TABLE_METRIC_COUNT_FIELDS,
    Table,
    TableId,
    TableMetrics,
    TableName,
)
from context.table_maintenance.application.port.inbound.table import ListTableMetricsUseCaseInput
from context.table_maintenance.application.service.table import ListTableMetricsService
from tests.context.table_maintenance.discovery_decision_samples import MANAGED, UNMANAGED

RULE_1 = "dr-00000000000000000000000001"


def _register(tables_repo, now, uuid, table_name="orders"):
    table = Table.register(
        TableId(uuid),
        TableName(catalog="iceberg", namespace="retail", table=table_name),
        MANAGED,
        now,
    )
    tables_repo.create(table)
    return table


def _metrics(uuid, now, **changes):
    counts = dict.fromkeys(TABLE_METRIC_COUNT_FIELDS, 0)
    return TableMetrics(table_id=TableId(uuid), observed_at=now, **{**counts, **changes})


def test_only_managed_tables_are_listed(tables_repo, metrics_store, now):
    """Rows of an unmanaged table, a dropped one and one the repo does not know are left out."""
    _register(tables_repo, now, "u-managed")
    _register(tables_repo, now, "u-unmanaged", "items").unmanage(UNMANAGED.match, now)
    _register(tables_repo, now, "u-dropped", "events").mark_dropped(now)
    for uuid in ("u-managed", "u-unmanaged", "u-dropped", "u-unknown"):
        metrics_store.save(_metrics(uuid, now))

    output = ListTableMetricsService(tables_repo, metrics_store).execute(ListTableMetricsUseCaseInput())

    assert [t.table_uuid for t in output.tables] == ["u-managed"]


def test_names_come_from_the_current_table_and_counts_from_the_row(tables_repo, metrics_store, now):
    """The listing carries the table's present name, the observation time and every count."""
    _register(tables_repo, now, "u-1")
    metrics_store.save(_metrics("u-1", now, data_files=12, snapshots=3))

    (entry,) = ListTableMetricsService(tables_repo, metrics_store).execute(ListTableMetricsUseCaseInput()).tables

    assert (entry.catalog, entry.namespace, entry.table) == ("iceberg", "retail", "orders")
    assert entry.observed_at == now
    assert set(entry.counts) == set(TABLE_METRIC_COUNT_FIELDS)
    assert entry.counts["data_files"] == 12
    assert entry.counts["snapshots"] == 3


def test_tables_are_ordered_by_uuid(tables_repo, metrics_store, now):
    """The listing is ordered by table uuid."""
    for uuid in ("u-3", "u-1", "u-2"):
        _register(tables_repo, now, uuid, f"t_{uuid}")
        metrics_store.save(_metrics(uuid, now))

    output = ListTableMetricsService(tables_repo, metrics_store).execute(ListTableMetricsUseCaseInput())

    assert [t.table_uuid for t in output.tables] == ["u-1", "u-2", "u-3"]
