"""Tests for the static summaries shown for each workflow in the Temporal UI."""

from __future__ import annotations

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_discovery import (
    table_discovery_summary,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    table_maintenance_summary,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance_admission import (
    table_maintenance_admission_summary,
)


def test_table_maintenance_summary_names_the_table_and_its_operations():
    assert (
        table_maintenance_summary("iceberg.e2e.tm_e2e_orders", ["rewrite_data_files", "expire_snapshots"])
        == "iceberg.e2e.tm_e2e_orders · rewrite_data_files, expire_snapshots"
    )


def test_table_discovery_summary_names_the_catalog():
    assert table_discovery_summary("iceberg", None) == "iceberg"


def test_table_discovery_summary_names_the_namespace_and_an_adhoc_trigger():
    assert table_discovery_summary("iceberg", "sales", adhoc=True) == "iceberg.sales · ad hoc"
    assert table_discovery_summary("iceberg", None, adhoc=True) == "iceberg · ad hoc"


def test_table_maintenance_admission_summary_names_the_limit():
    assert table_maintenance_admission_summary(2) == "global Spark maintenance admission (limit=2)"
