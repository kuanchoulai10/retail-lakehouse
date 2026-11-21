"""Test the GetTableCurrentMetricsService."""

from __future__ import annotations

import pytest

from context.table_maintenance.application.domain.model.table import (
    TABLE_METRIC_COUNT_FIELDS,
    Table,
    TableId,
    TableMetrics,
    TableName,
)
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table import GetTableCurrentMetricsUseCaseInput
from context.table_maintenance.application.service.table import GetTableCurrentMetricsService
from tests.context.table_maintenance.discovery_decision_samples import MANAGED, UNMANAGED

RULE_1 = "dr-00000000000000000000000001"


def _register(tables_repo, now, uuid):
    table = Table.register(
        TableId(uuid),
        TableName(catalog="iceberg", namespace="retail", table="orders"),
        MANAGED,
        now,
    )
    tables_repo.create(table)
    return table


def _metrics(uuid, now, **changes):
    counts = dict.fromkeys(TABLE_METRIC_COUNT_FIELDS, 0)
    return TableMetrics(table_id=TableId(uuid), observed_at=now, **{**counts, **changes})


def _service(tables_repo, metrics_store):
    return GetTableCurrentMetricsService(tables_repo, metrics_store)


def test_a_managed_table_with_a_row_returns_its_counts(tables_repo, metrics_store, now):
    """The output carries the observation time and every count of the saved row."""
    _register(tables_repo, now, "u-1")
    metrics_store.save(_metrics("u-1", now, data_files=12, snapshots=3))

    output = _service(tables_repo, metrics_store).execute(GetTableCurrentMetricsUseCaseInput(uuid="u-1"))

    assert output.observed_at == now
    assert output.counts is not None
    assert set(output.counts) == set(TABLE_METRIC_COUNT_FIELDS)
    assert output.counts["data_files"] == 12
    assert output.counts["snapshots"] == 3


def test_a_managed_table_with_no_row_returns_nothing(tables_repo, metrics_store, now):
    """A table not reconciled yet has no metrics."""
    _register(tables_repo, now, "u-1")

    output = _service(tables_repo, metrics_store).execute(GetTableCurrentMetricsUseCaseInput(uuid="u-1"))

    assert (output.observed_at, output.counts) == (None, None)


def test_an_unmanaged_table_with_a_stale_row_returns_nothing(tables_repo, metrics_store, now):
    """A row left behind by a table that left maintenance is not shown."""
    _register(tables_repo, now, "u-1").unmanage(UNMANAGED.match, now)
    metrics_store.save(_metrics("u-1", now, data_files=12))

    output = _service(tables_repo, metrics_store).execute(GetTableCurrentMetricsUseCaseInput(uuid="u-1"))

    assert (output.observed_at, output.counts) == (None, None)


def test_a_dropped_table_with_a_stale_row_returns_nothing(tables_repo, metrics_store, now):
    """A dropped table shows no metrics either."""
    _register(tables_repo, now, "u-1").mark_dropped(now)
    metrics_store.save(_metrics("u-1", now, data_files=12))

    output = _service(tables_repo, metrics_store).execute(GetTableCurrentMetricsUseCaseInput(uuid="u-1"))

    assert (output.observed_at, output.counts) == (None, None)


def test_an_unknown_table_raises_not_found(tables_repo, metrics_store):
    """A uuid the repo does not know is a NotFoundError."""
    with pytest.raises(NotFoundError):
        _service(tables_repo, metrics_store).execute(GetTableCurrentMetricsUseCaseInput(uuid="u-nope"))
