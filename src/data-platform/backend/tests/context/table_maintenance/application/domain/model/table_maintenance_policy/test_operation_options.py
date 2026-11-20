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


def test_rewrite_options_render_iceberg_spelling() -> None:
    """Check set options are rendered in Iceberg's spelling."""
    options = RewriteDataFilesOptions(min_input_files=2, partial_progress_enabled=True, partial_progress_max_commits=3)
    assert options.procedure_options() == {
        "min-input-files": 2,
        "partial-progress.enabled": True,
        "partial-progress.max-commits": 3,
    }
    assert options.procedure_arguments() == {}


def test_rewrite_options_render_every_option() -> None:
    """Check every option has its Iceberg spelling."""
    options = RewriteDataFilesOptions(
        strategy=RewriteDataFilesStrategy.SORT,
        sort_order="zorder(a, b)",
        min_input_files=2,
        partial_progress_enabled=True,
        partial_progress_max_commits=3,
        max_concurrent_file_group_rewrites=4,
        rewrite_all=False,
        delete_file_threshold=5,
        remove_dangling_deletes=True,
        max_file_group_size_bytes=6,
    )
    assert options.procedure_arguments() == {"strategy": "sort", "sort_order": "zorder(a, b)"}
    assert options.procedure_options() == {
        "min-input-files": 2,
        "partial-progress.enabled": True,
        "partial-progress.max-commits": 3,
        "max-concurrent-file-group-rewrites": 4,
        "rewrite-all": False,
        "delete-file-threshold": 5,
        "remove-dangling-deletes": True,
        "max-file-group-size-bytes": 6,
    }


def test_unset_rewrite_options_render_nothing() -> None:
    """Check an unset option is left to the procedure."""
    assert RewriteDataFilesOptions().procedure_arguments() == {}
    assert RewriteDataFilesOptions().procedure_options() == {}


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


def test_manifest_options_render_arguments() -> None:
    """Check use_caching is the only manifest option."""
    assert RewriteManifestsOptions(use_caching=False).procedure_arguments() == {"use_caching": False}
    assert RewriteManifestsOptions().procedure_arguments() == {}


def test_expire_options_render_arguments() -> None:
    """Check the expire options are rendered when set."""
    options = ExpireSnapshotsOptions(max_concurrent_deletes=4, stream_results=True)
    assert options.procedure_arguments() == {"max_concurrent_deletes": 4, "stream_results": True}
    assert ExpireSnapshotsOptions().procedure_arguments() == {}


def test_orphan_options_render_arguments() -> None:
    """Check the orphan options are rendered when set."""
    options = RemoveOrphanFilesOptions(max_concurrent_deletes=4, prefix_mismatch_mode=PrefixMismatchMode.IGNORE)
    assert options.procedure_arguments() == {"max_concurrent_deletes": 4, "prefix_mismatch_mode": "IGNORE"}
    assert RemoveOrphanFilesOptions().procedure_arguments() == {}


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
    assert spec.to_primitives() == {
        "target": data["target"],
        "options": {
            "strategy": None,
            "sort_order": None,
            "min_input_files": 2,
            "partial_progress_enabled": True,
            "partial_progress_max_commits": None,
            "max_concurrent_file_group_rewrites": None,
            "rewrite_all": None,
            "delete_file_threshold": None,
            "remove_dangling_deletes": None,
            "max_file_group_size_bytes": None,
        },
    }
