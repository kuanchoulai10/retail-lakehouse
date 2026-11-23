"""Test the option value objects and the operation specs."""

from __future__ import annotations

from typing import Any

import pytest

from base import InvariantViolation
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    ExpireSnapshotsOptions,
    PrefixMismatchMode,
    RemoveOrphanFilesOptions,
    RewriteDataFilesOptions,
    RewriteDataFilesSpec,
    RewriteDataFilesStrategy,
    RewriteManifestsOptions,
    RewriteManifestsSpec,
)


def test_sort_order_needs_the_sort_strategy() -> None:
    """Check a sort order without the sort strategy is refused."""
    with pytest.raises(InvariantViolation):
        RewriteDataFilesOptions.from_primitives({"sort_order": "a"})
    with pytest.raises(InvariantViolation):
        RewriteDataFilesOptions.from_primitives({"strategy": "binpack", "sort_order": "a"})
    assert RewriteDataFilesOptions.from_primitives({"strategy": "sort", "sort_order": "a"}).sort_order == "a"


@pytest.mark.parametrize("sort_order", ["", "a" * 1001])
def test_sort_order_length_is_bounded(sort_order: str) -> None:
    """Check an empty or over-long sort order is refused."""
    with pytest.raises(InvariantViolation):
        RewriteDataFilesOptions.from_primitives({"strategy": "sort", "sort_order": sort_order})


def test_max_commits_needs_partial_progress() -> None:
    """Check max commits without partial progress turned on is refused."""
    with pytest.raises(InvariantViolation):
        RewriteDataFilesOptions.from_primitives({"partial_progress_max_commits": 3})
    with pytest.raises(InvariantViolation):
        RewriteDataFilesOptions.from_primitives(
            {"partial_progress_enabled": False, "partial_progress_max_commits": 3},
        )


@pytest.mark.parametrize(
    "key",
    [
        "min_input_files",
        "partial_progress_max_commits",
        "max_concurrent_file_group_rewrites",
        "delete_file_threshold",
        "max_file_group_size_bytes",
    ],
)
def test_rewrite_integers_are_positive(key: str) -> None:
    """Check integer options must be positive."""
    with pytest.raises(InvariantViolation):
        RewriteDataFilesOptions.from_primitives({"partial_progress_enabled": True, key: 0})


@pytest.mark.parametrize(
    ("options_type", "key"),
    [
        (RewriteDataFilesOptions, "target_file_size_bytes"),
        (RewriteDataFilesOptions, "where"),
        (ExpireSnapshotsOptions, "retain_last"),
        (ExpireSnapshotsOptions, "older_than"),
        (RemoveOrphanFilesOptions, "older_than"),
        (RemoveOrphanFilesOptions, "dry_run"),
        (RemoveOrphanFilesOptions, "location"),
    ],
)
def test_values_owned_by_the_target_or_platform_are_not_options(options_type: Any, key: str) -> None:
    """Check keys the target or the platform owns are refused as options."""
    with pytest.raises(InvariantViolation):
        options_type.from_primitives({key: 1})


def test_unknown_prefix_mismatch_mode_is_refused() -> None:
    """Check only the three Iceberg modes are accepted."""
    with pytest.raises(InvariantViolation):
        RemoveOrphanFilesOptions.from_primitives({"prefix_mismatch_mode": "warn"})
    assert RemoveOrphanFilesOptions.from_primitives({"prefix_mismatch_mode": "DELETE"}).prefix_mismatch_mode is (
        PrefixMismatchMode.DELETE
    )


def test_a_spec_without_options_reads_none() -> None:
    """Check a spec may leave its options out."""
    spec = RewriteManifestsSpec.from_primitives({"target": {"small_manifests": {"at_most": 5}}})
    assert spec.options is None


def test_a_spec_reads_target_and_options() -> None:
    """Check a spec nests its target and options, and writes them back."""
    data = {
        "target": {"reducible_files": {"at_most": 5}, "per": "partition"},
        "options": {"min_input_files": 2, "partial_progress_enabled": True},
    }
    spec = RewriteDataFilesSpec.from_primitives(data)
    assert spec.options is not None
    assert spec.options.min_input_files == 2
    assert spec.to_primitives() == data


def test_a_spec_without_options_dumps_null_and_round_trips() -> None:
    """Check an absent options object is written as null and read back equal."""
    spec = RewriteManifestsSpec.from_primitives({"target": {"small_manifests": {"at_most": 5}}})
    assert spec.to_primitives() == {"target": {"small_manifests": {"at_most": 5}}, "options": None}
    assert RewriteManifestsSpec.from_primitives(spec.to_primitives()) == spec


def test_unset_options_are_left_out_of_the_primitives() -> None:
    """Check only the options that are set are written."""
    assert RewriteDataFilesOptions().to_primitives() == {}
    assert RewriteManifestsOptions().to_primitives() == {}
    assert ExpireSnapshotsOptions(stream_results=False).to_primitives() == {"stream_results": False}
    assert RemoveOrphanFilesOptions(prefix_mismatch_mode=PrefixMismatchMode.ERROR).to_primitives() == {
        "prefix_mismatch_mode": "ERROR",
    }


@pytest.mark.parametrize(
    "options",
    [
        RewriteDataFilesOptions(
            strategy=RewriteDataFilesStrategy.SORT,
            sort_order="a",
            min_input_files=2,
            partial_progress_enabled=True,
            partial_progress_max_commits=3,
            rewrite_all=False,
        ),
        RewriteManifestsOptions(use_caching=True),
        ExpireSnapshotsOptions(max_concurrent_deletes=4),
        RemoveOrphanFilesOptions(max_concurrent_deletes=4, prefix_mismatch_mode=PrefixMismatchMode.DELETE),
    ],
)
def test_options_round_trip_through_primitives(options: Any) -> None:
    """Check options with some keys set survive the wire."""
    assert type(options).from_primitives(options.to_primitives()) == options
