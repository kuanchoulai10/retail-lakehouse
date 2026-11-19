"""Tests for the static summaries shown for each workflow in the Temporal UI."""

from __future__ import annotations

from context.table_maintenance.adapter.hybrid.temporal.contracts.compaction_round import (
    compaction_round_details,
    compaction_round_summary,
)
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


def test_table_maintenance_admission_summary_names_the_limit():
    """The admission summary states the concurrency limit."""
    assert table_maintenance_admission_summary(2) == "global Spark maintenance admission (limit=2)"


def test_compaction_round_summary_names_the_budget():
    """A scheduled round's summary says what it may grant."""
    assert compaction_round_summary(0.05) == "compaction round · budget 0.05 GB·h"


def test_compaction_round_details_count_partitions_and_tables():
    """A round's details name its round id, so the console's round is found in Temporal, then what it granted."""
    round_id = "cr-00000000000000000000000001"
    assert compaction_round_details(round_id, 3, 2) == f"round {round_id} · granted 3 partitions of 2 tables"
    assert compaction_round_details(round_id, 1, 1) == f"round {round_id} · granted 1 partition of 1 table"
    assert compaction_round_details(round_id, 0, 0) == f"round {round_id} · granted 0 partitions of 0 tables"
