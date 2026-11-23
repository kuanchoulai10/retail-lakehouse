"""Write the Iceberg procedure arguments of a maintenance job."""

from __future__ import annotations

from datetime import UTC
from typing import TYPE_CHECKING, Any

from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    ExpireSnapshotsJob,
    RemoveOrphanFilesJob,
    RewriteDataFilesJob,
    RewriteManifestsJob,
)

if TYPE_CHECKING:
    from datetime import datetime


def iceberg_procedure_args(
    job: RewriteDataFilesJob | RewriteManifestsJob | ExpireSnapshotsJob | RemoveOrphanFilesJob,
) -> dict[str, Any]:
    """Return the named arguments of the job's Iceberg procedure, only those that are set.

    ``rewrite_data_files`` takes ``strategy`` and ``sort_order`` as arguments and the rest in its
    ``options`` map, under Iceberg's hyphenated names, ``target-file-size-bytes`` first; the map is
    written in that fixed order, which is the order of ``map(...)`` in the ``CALL``. ``older_than`` is
    the instant in UTC as ISO-8601 with a ``+00:00`` offset.
    """
    match job:
        case RewriteDataFilesJob():
            return _rewrite_data_files_args(job)
        case RewriteManifestsJob():
            return {} if job.use_caching is None else {"use_caching": job.use_caching}
        case ExpireSnapshotsJob():
            return _set(
                older_than=_utc_text(job.older_than),
                retain_last=job.retain_last,
                max_concurrent_deletes=job.max_concurrent_deletes,
                stream_results=job.stream_results,
            )
        case RemoveOrphanFilesJob():
            return _set(
                older_than=_utc_text(job.older_than),
                max_concurrent_deletes=job.max_concurrent_deletes,
                prefix_mismatch_mode=job.prefix_mismatch_mode,
            )


def _rewrite_data_files_args(job: RewriteDataFilesJob) -> dict[str, Any]:
    options = _set(
        **{
            "target-file-size-bytes": job.target_file_size_bytes,
            "min-input-files": job.min_input_files,
            "partial-progress.enabled": job.partial_progress_enabled,
            "partial-progress.max-commits": job.partial_progress_max_commits,
            "max-concurrent-file-group-rewrites": job.max_concurrent_file_group_rewrites,
            "rewrite-all": job.rewrite_all,
            "delete-file-threshold": job.delete_file_threshold,
            "remove-dangling-deletes": job.remove_dangling_deletes,
            "max-file-group-size-bytes": job.max_file_group_size_bytes,
        }
    )
    return {**_set(strategy=job.strategy, sort_order=job.sort_order), "options": options}


def _set(**arguments: Any) -> dict[str, Any]:  # noqa: ANN401
    return {name: value for name, value in arguments.items() if value is not None}


def _utc_text(moment: datetime) -> str:
    if moment.tzinfo is None:
        raise ValueError("older_than must be timezone-aware")
    return moment.astimezone(UTC).isoformat()
