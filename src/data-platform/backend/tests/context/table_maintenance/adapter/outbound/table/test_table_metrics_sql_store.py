"""Test the stores of a table's newest metrics."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.exc import IntegrityError

from context.table_maintenance.adapter.outbound.table.sql import TableMetricsSqlStore, table_metrics_table
from context.table_maintenance.application.domain.model.table import TABLE_METRIC_COUNT_FIELDS
from context.table_maintenance.application.port.outbound.table import TableId, TableMetrics
from tests.context.table_maintenance.fakes.in_memory_table_metrics_store import InMemoryTableMetricsStore

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from context.table_maintenance.application.port.outbound.table import TableMetricsStore

NOW = datetime(2026, 11, 20, 12, tzinfo=UTC)


def _metrics(table_uuid: str = "t-1", *, at: datetime = NOW, count: int = 1) -> TableMetrics:
    counts = {name: count + index for index, name in enumerate(TABLE_METRIC_COUNT_FIELDS)}
    return TableMetrics(table_id=TableId(table_uuid), observed_at=at, **counts)


@pytest.fixture(params=["sql", "memory"])
def store(request: pytest.FixtureRequest, engine: Engine) -> TableMetricsStore:
    """Provide each store implementation."""
    if request.param == "sql":
        return TableMetricsSqlStore(engine)
    return InMemoryTableMetricsStore()


def test_save_then_get_round_trips(store: TableMetricsStore):
    """Saved metrics load back equal, with an aware time."""
    saved = _metrics()
    store.save(saved)

    loaded = store.get(TableId("t-1"))
    assert loaded is not None
    assert loaded.model_dump() == saved.model_dump()
    assert loaded.observed_at.tzinfo is not None


def test_unknown_table_is_none(store: TableMetricsStore):
    """A table never measured reads as None."""
    assert store.get(TableId("nope")) is None


def test_newer_metrics_replace_older(store: TableMetricsStore):
    """Metrics observed later replace the stored ones, keeping one row per table."""
    store.save(_metrics(at=NOW, count=1))
    store.save(_metrics(at=NOW + timedelta(minutes=10), count=100))

    (only,) = store.list_all()
    assert only == _metrics(at=NOW + timedelta(minutes=10), count=100)


def test_older_metrics_never_replace_newer(store: TableMetricsStore):
    """A retried reconcile with an older observation, saved last, leaves the newer metrics."""
    store.save(_metrics(at=NOW + timedelta(minutes=10), count=100))
    store.save(_metrics(at=NOW, count=1))

    assert store.get(TableId("t-1")) == _metrics(at=NOW + timedelta(minutes=10), count=100)


def test_metrics_observed_at_the_same_time_leave_the_stored_ones(store: TableMetricsStore):
    """Only a later observation replaces the stored one."""
    store.save(_metrics(at=NOW, count=1))
    store.save(_metrics(at=NOW, count=100))

    assert store.get(TableId("t-1")) == _metrics(at=NOW, count=1)


def test_two_first_saves_race_to_the_newer(engine: Engine, monkeypatch: pytest.MonkeyPatch):
    """Both saves found no row; the one whose insert hits the other's row tries again as the update."""
    store = TableMetricsSqlStore(engine)
    original = store._save_once
    calls: list[datetime] = []

    def racing(metrics: TableMetrics) -> None:
        calls.append(metrics.observed_at)
        if len(calls) == 1:
            original(_metrics(at=NOW, count=1))
            raise IntegrityError("INSERT", {}, Exception("UNIQUE constraint failed: table_metrics.table_uuid"))
        original(metrics)

    monkeypatch.setattr(store, "_save_once", racing)
    store.save(_metrics(at=NOW + timedelta(minutes=10), count=100))

    assert len(calls) == 2
    assert store.get(TableId("t-1")) == _metrics(at=NOW + timedelta(minutes=10), count=100)


def test_delete_removes_the_row_and_tolerates_absence(store: TableMetricsStore):
    """Deleting a table's metrics removes them, and deleting again is no error."""
    store.save(_metrics())
    store.delete(TableId("t-1"))
    store.delete(TableId("t-1"))

    assert store.get(TableId("t-1")) is None


def test_list_all_orders_by_table_uuid(store: TableMetricsStore):
    """Every table's metrics are listed, by table uuid."""
    store.save(_metrics("t-b"))
    store.save(_metrics("t-a"))

    assert [m.table_id.value for m in store.list_all()] == ["t-a", "t-b"]


def test_table_metrics_sql_table_name():
    """The metrics live in the table_metrics table."""
    assert table_metrics_table.name == "table_metrics"
