"""Test the Iceberg procedure arguments the Spark adapter writes for each kind of job."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta, timezone

from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s import iceberg_procedure_args
from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    ExpireSnapshotsJob,
    RemoveOrphanFilesJob,
    RewriteDataFilesJob,
    RewriteManifestsJob,
)

NOW = datetime(2026, 10, 24, 12, tzinfo=UTC)


def test_rewrite_args_carry_the_options_map():
    """A compaction's options go in Iceberg's spelling into the options map, after the target file size."""
    job = RewriteDataFilesJob(target_file_size_bytes=536870912, min_input_files=2, partial_progress_enabled=True)
    assert iceberg_procedure_args(job) == {
        "options": {"target-file-size-bytes": 536870912, "min-input-files": 2, "partial-progress.enabled": True}
    }


def test_rewrite_args_with_sort_strategy():
    """The strategy and the sort order are top-level arguments, the rest stays in the options map."""
    job = RewriteDataFilesJob(
        target_file_size_bytes=536870912,
        strategy="sort",
        sort_order="id DESC",
        partial_progress_enabled=True,
        partial_progress_max_commits=3,
        rewrite_all=True,
        max_file_group_size_bytes=1024,
    )
    assert iceberg_procedure_args(job) == {
        "strategy": "sort",
        "sort_order": "id DESC",
        "options": {
            "target-file-size-bytes": 536870912,
            "partial-progress.enabled": True,
            "partial-progress.max-commits": 3,
            "rewrite-all": True,
            "max-file-group-size-bytes": 1024,
        },
    }


def test_rewrite_options_keep_their_order():
    """The options map is written in one fixed order, which is the order of ``map(...)`` in the call."""
    job = RewriteDataFilesJob(
        target_file_size_bytes=1,
        max_file_group_size_bytes=8,
        remove_dangling_deletes=False,
        delete_file_threshold=7,
        rewrite_all=False,
        max_concurrent_file_group_rewrites=6,
        partial_progress_max_commits=5,
        partial_progress_enabled=True,
        min_input_files=4,
    )
    assert list(iceberg_procedure_args(job)["options"]) == [
        "target-file-size-bytes",
        "min-input-files",
        "partial-progress.enabled",
        "partial-progress.max-commits",
        "max-concurrent-file-group-rewrites",
        "rewrite-all",
        "delete-file-threshold",
        "remove-dangling-deletes",
        "max-file-group-size-bytes",
    ]


def test_rewrite_args_without_options_carry_only_the_size():
    """A compaction without options leaves every option to the procedure."""
    assert iceberg_procedure_args(RewriteDataFilesJob(target_file_size_bytes=536870912)) == {
        "options": {"target-file-size-bytes": 536870912}
    }


def test_rewrite_args_leave_the_partitions_to_the_where_clause():
    """The partitions of a compaction are its where clause, never a procedure argument."""
    args = iceberg_procedure_args(RewriteDataFilesJob(target_file_size_bytes=1))
    assert "where" not in args
    assert "partitions" not in json.dumps(args)


def test_expire_args_carry_the_retention_and_their_options():
    """Snapshot expiry passes its age as an ISO time in UTC, the number to keep and its set options."""
    job = ExpireSnapshotsJob(
        older_than=NOW - timedelta(days=2), retain_last=4, max_concurrent_deletes=8, stream_results=True
    )
    assert iceberg_procedure_args(job) == {
        "older_than": "2026-10-22T12:00:00+00:00",
        "retain_last": 4,
        "max_concurrent_deletes": 8,
        "stream_results": True,
    }
    assert iceberg_procedure_args(ExpireSnapshotsJob(older_than=NOW, retain_last=10)) == {
        "older_than": "2026-10-24T12:00:00+00:00",
        "retain_last": 10,
    }


def test_older_than_is_written_in_utc_with_its_microseconds():
    """A time in another zone is written as the same instant in UTC, ``+00:00`` and microseconds kept."""
    taipei = datetime(2026, 10, 22, 20, 15, 30, 123456, tzinfo=timezone(timedelta(hours=8)))
    assert iceberg_procedure_args(RemoveOrphanFilesJob(older_than=taipei)) == {
        "older_than": "2026-10-22T12:15:30.123456+00:00"
    }


def test_manifest_args_carry_their_options():
    """A manifest rewrite passes ``use_caching`` only when it is set."""
    assert iceberg_procedure_args(RewriteManifestsJob()) == {}
    assert iceberg_procedure_args(RewriteManifestsJob(use_caching=False)) == {"use_caching": False}


def test_orphan_args_carry_prefix_mismatch_mode():
    """Orphan removal passes its age and its set options."""
    assert iceberg_procedure_args(RemoveOrphanFilesJob(older_than=NOW - timedelta(days=3))) == {
        "older_than": "2026-10-21T12:00:00+00:00"
    }
    job = RemoveOrphanFilesJob(
        older_than=NOW - timedelta(days=2), max_concurrent_deletes=4, prefix_mismatch_mode="IGNORE"
    )
    assert iceberg_procedure_args(job) == {
        "older_than": "2026-10-22T12:00:00+00:00",
        "max_concurrent_deletes": 4,
        "prefix_mismatch_mode": "IGNORE",
    }
