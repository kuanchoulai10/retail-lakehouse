"""Serialize TableProperties to a flat dict for output DTOs."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from application.domain.model.catalog.table_properties.delete_properties import (
        DeleteProperties,
    )
    from application.domain.model.catalog.table_properties.table_properties import (
        TableProperties,
    )


def table_properties_to_dict(props: TableProperties) -> dict[str, str]:
    """Flatten a TableProperties VO to a dict[str, str] for output DTOs."""
    result: dict[str, str] = {}

    if props.format_version is not None:
        result["format-version"] = str(props.format_version)

    if props.write is not None:
        w = props.write
        _put_operation(result, "write.merge", w.merge)
        _put_operation(result, "write.update", w.update)
        _put_delete(result, w.delete)
        _put(result, "write.distribution-mode", w.distribution_mode)
        if w.format is not None:
            _put(result, "write.format.default", w.format.default)
        _put_parquet(result, "write.parquet", w.parquet)
        _put(result, "write.target-file-size-bytes", w.target_file_size_bytes)
        if w.manifest is not None:
            _put(
                result, "write.manifest.target-size-bytes", w.manifest.target_size_bytes
            )
            _put(result, "write.manifest.min-merge-count", w.manifest.min_merge_count)
            _put_bool(result, "write.manifest.merge.enabled", w.manifest.merge_enabled)
        if w.metadata is not None:
            _put(
                result, "write.metadata.compression-codec", w.metadata.compression_codec
            )
            _put_bool(
                result,
                "write.metadata.delete-after-commit.enabled",
                w.metadata.delete_after_commit_enabled,
            )
            _put(
                result,
                "write.metadata.previous-versions-max",
                w.metadata.previous_versions_max,
            )
        if w.commit is not None:
            _put(result, "write.commit.num-retries", w.commit.num_retries)
            _put(result, "write.commit.retry.min-wait-ms", w.commit.retry_min_wait_ms)
            _put(result, "write.commit.retry.max-wait-ms", w.commit.retry_max_wait_ms)
            _put(
                result,
                "write.commit.retry.total-timeout-ms",
                w.commit.total_retry_time_ms,
            )
        if w.metrics is not None:
            _put(result, "write.metrics.mode", w.metrics.default_mode)
        _put_bool(result, "write.upsert.enabled", w.upsert_enabled)
        _put_bool(result, "write.wap.enabled", w.wap_enabled)
        _put_bool(result, "write.object-storage.enabled", w.object_storage_enabled)

    if props.read is not None:
        r = props.read
        if r.split is not None:
            _put(result, "read.split.planning.size", r.split.size)
            _put(result, "read.split.planning.lookback", r.split.lookback)
            _put(result, "read.split.planning.open-file-cost", r.split.open_file_cost)
        if r.parquet is not None:
            _put_bool(
                result,
                "read.parquet.vectorization.enabled",
                r.parquet.vectorization_enabled,
            )
            _put(result, "read.parquet.batch-size", r.parquet.batch_size)
        if r.orc is not None:
            _put_bool(
                result, "read.orc.vectorization.enabled", r.orc.vectorization_enabled
            )
            _put(result, "read.orc.batch-size", r.orc.batch_size)

    return result


def _put_operation(result: dict[str, str], prefix: str, op: object | None) -> None:
    if op is None:
        return
    _put(result, f"{prefix}.mode", getattr(op, "mode", None))
    _put(result, f"{prefix}.isolation-level", getattr(op, "isolation_level", None))
    _put(result, f"{prefix}.distribution-mode", getattr(op, "distribution_mode", None))


def _put_delete(result: dict[str, str], d: DeleteProperties | None) -> None:
    if d is None:
        return
    _put(result, "write.delete.mode", d.mode)
    _put(result, "write.delete.isolation-level", d.isolation_level)
    _put(result, "write.delete.distribution-mode", d.distribution_mode)
    _put(result, "write.delete.format.default", d.format_default)
    _put(result, "write.delete.target-file-size-bytes", d.target_file_size_bytes)
    _put_parquet(result, "write.delete.parquet", d.parquet)


def _put_parquet(result: dict[str, str], prefix: str, p: object | None) -> None:
    if p is None:
        return
    _put(result, f"{prefix}.compression-codec", getattr(p, "compression_codec", None))
    _put(result, f"{prefix}.compression-level", getattr(p, "compression_level", None))
    _put(
        result,
        f"{prefix}.row-group-size-bytes",
        getattr(p, "row_group_size_bytes", None),
    )
    _put(result, f"{prefix}.page-size-bytes", getattr(p, "page_size_bytes", None))
    _put(result, f"{prefix}.dict-size-bytes", getattr(p, "dict_size_bytes", None))


def _put(result: dict[str, str], key: str, value: object | None) -> None:
    if value is not None:
        result[key] = str(value)


def _put_bool(result: dict[str, str], key: str, value: bool | None) -> None:
    if value is not None:
        result[key] = "true" if value else "false"
