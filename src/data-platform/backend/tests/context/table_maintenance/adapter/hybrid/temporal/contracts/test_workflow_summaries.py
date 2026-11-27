"""Tests for the static summaries shown for each workflow in the Temporal UI."""

from __future__ import annotations

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_discovery import (
    table_discovery_summary,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_discovery_round import (
    TABLE_DISCOVERY_ROUND_SUMMARY,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    table_maintenance_summary,
)


def test_table_maintenance_summary_names_the_table_and_its_operations():
    """The maintenance summary names the table and its operations."""
    assert (
        table_maintenance_summary("iceberg.e2e.tm_e2e_orders", ["rewrite_data_files", "expire_snapshots"])
        == "iceberg.e2e.tm_e2e_orders · rewrite_data_files, expire_snapshots"
    )


def test_table_discovery_summary_names_the_catalog():
    """Without a namespace the discovery summary is just the catalog name."""
    assert table_discovery_summary("iceberg", None) == "iceberg"


def test_table_discovery_summary_names_the_namespace_and_an_adhoc_trigger():
    """The discovery summary adds the namespace and an ad hoc marker when present."""
    assert table_discovery_summary("iceberg", "sales", adhoc=True) == "iceberg.sales · ad hoc"
    assert table_discovery_summary("iceberg", None, adhoc=True) == "iceberg · ad hoc"


def test_table_discovery_round_summary_says_it_scans_every_scanned_catalog():
    """The round's summary says it starts a scan of every scanned catalog."""
    assert TABLE_DISCOVERY_ROUND_SUMMARY == "every scanned catalog"
