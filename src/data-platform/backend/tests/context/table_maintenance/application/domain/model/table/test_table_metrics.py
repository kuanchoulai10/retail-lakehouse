"""Test the TableMetrics value object."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from base import InvariantViolation
from context.table_maintenance.application.domain.model.shared import TableId
from context.table_maintenance.application.domain.model.table import TABLE_METRIC_COUNT_FIELDS, TableMetrics

NOW = datetime(2026, 11, 20, 12, tzinfo=UTC)


def metrics(**changes: int) -> TableMetrics:
    """Build metrics with every count 1, then apply ``changes``."""
    counts = dict.fromkeys(TABLE_METRIC_COUNT_FIELDS, 1)
    return TableMetrics(table_id=TableId("t1"), observed_at=NOW, **{**counts, **changes})


def test_count_fields_name_every_count_in_order():
    """The count constant lists exactly the integer fields, in the documented order."""
    assert TABLE_METRIC_COUNT_FIELDS == (
        "data_files",
        "position_delete_files",
        "equality_delete_files",
        "deletion_vectors",
        "data_size_bytes",
        "data_records",
        "position_delete_records",
        "equality_delete_records",
        "reducible_files",
        "manifests",
        "manifests_size_bytes",
        "manifest_added_entries",
        "manifest_existing_entries",
        "manifest_deleted_entries",
        "snapshots",
    )
    assert set(TABLE_METRIC_COUNT_FIELDS) == set(TableMetrics.model_fields) - {"table_id", "observed_at"}


def test_metrics_hold_what_they_are_built_with():
    """A valid value keeps its identity, time and counts."""
    m = metrics(data_files=7)
    assert m.table_id == TableId("t1")
    assert m.observed_at == NOW
    assert m.data_files == 7


@pytest.mark.parametrize("field", TABLE_METRIC_COUNT_FIELDS)
def test_negative_count_is_refused(field: str):
    """Every count refuses a negative number."""
    with pytest.raises(InvariantViolation):
        metrics(**{field: -1})


def test_naive_observed_at_is_refused():
    """The observation time must carry a timezone."""
    with pytest.raises(InvariantViolation):
        TableMetrics(
            table_id=TableId("t1"),
            observed_at=datetime(2026, 11, 20, 12),  # noqa: DTZ001
            **dict.fromkeys(TABLE_METRIC_COUNT_FIELDS, 1),
        )
