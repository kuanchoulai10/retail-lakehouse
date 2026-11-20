"""Test the derive_metric_trend_values domain service."""

from __future__ import annotations

from context.table_maintenance.application.domain.service.table import derive_metric_trend_values


def test_averages_divide_by_manifests() -> None:
    """The average size and the average entries are totals divided by the manifests."""
    got = derive_metric_trend_values(
        {
            "manifests": 4,
            "manifests_size_bytes": 400,
            "manifest_added_entries": 6,
            "manifest_existing_entries": 2,
            "manifest_deleted_entries": 0,
        }
    )

    assert got["manifest_average_size_bytes"] == 100
    assert got["manifest_average_entries"] == 2


def test_the_input_values_are_kept() -> None:
    """The derived values come in addition to the given ones."""
    got = derive_metric_trend_values({"manifests": 4, "data_files": 7})

    assert got["data_files"] == 7
    assert got["manifests"] == 4


def test_averages_are_null_without_manifests() -> None:
    """Zero or missing manifests give null averages, never a division error."""
    for manifests in (0, None):
        got = derive_metric_trend_values(
            {
                "manifests": manifests,
                "manifests_size_bytes": 400,
                "manifest_added_entries": 6,
                "manifest_existing_entries": 2,
                "manifest_deleted_entries": 0,
            }
        )

        assert got["manifest_average_size_bytes"] is None
        assert got["manifest_average_entries"] is None


def test_averages_are_null_when_a_total_is_missing() -> None:
    """A total Prometheus has no value for leaves its average null."""
    got = derive_metric_trend_values(
        {
            "manifests": 4,
            "manifests_size_bytes": None,
            "manifest_added_entries": 6,
            "manifest_existing_entries": None,
            "manifest_deleted_entries": 0,
        }
    )

    assert got["manifest_average_size_bytes"] is None
    assert got["manifest_average_entries"] is None
