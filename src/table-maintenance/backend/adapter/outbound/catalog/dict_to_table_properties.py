"""Convert a raw Iceberg properties dict to a typed TableProperties value object."""

from __future__ import annotations

from enum import StrEnum

from application.domain.model.catalog.table_properties.commit_properties import (
    CommitProperties,
)
from application.domain.model.catalog.table_properties.delete_properties import (
    DeleteProperties,
)
from application.domain.model.catalog.table_properties.distribution_mode import (
    DistributionMode,
)
from application.domain.model.catalog.table_properties.format_properties import (
    FormatProperties,
)
from application.domain.model.catalog.table_properties.isolation_level import (
    IsolationLevel,
)
from application.domain.model.catalog.table_properties.manifest_properties import (
    ManifestProperties,
)
from application.domain.model.catalog.table_properties.metadata_properties import (
    MetadataProperties,
)
from application.domain.model.catalog.table_properties.metrics_properties import (
    MetricsProperties,
)
from application.domain.model.catalog.table_properties.operation_properties import (
    OperationProperties,
)
from application.domain.model.catalog.table_properties.parquet_properties import (
    ParquetProperties,
)
from application.domain.model.catalog.table_properties.read_orc_properties import (
    ReadOrcProperties,
)
from application.domain.model.catalog.table_properties.read_parquet_properties import (
    ReadParquetProperties,
)
from application.domain.model.catalog.table_properties.read_properties import (
    ReadProperties,
)
from application.domain.model.catalog.table_properties.split_properties import (
    SplitProperties,
)
from application.domain.model.catalog.table_properties.table_properties import (
    TableProperties,
)
from application.domain.model.catalog.table_properties.write_mode import WriteMode
from application.domain.model.catalog.table_properties.write_properties import (
    WriteProperties,
)


def dict_to_table_properties(raw: dict[str, str]) -> TableProperties:
    """Convert a raw Iceberg properties dict to a typed TableProperties."""
    return TableProperties(
        format_version=_int(raw.get("format-version")),
        write=_build_write(raw),
        read=_build_read(raw),
    )


# --- Write ---


def _build_write(raw: dict[str, str]) -> WriteProperties | None:
    merge = _build_operation(raw, "write.merge")
    update = _build_operation(raw, "write.update")
    delete = _build_delete(raw)
    distribution_mode = _enum(DistributionMode, raw.get("write.distribution-mode"))
    fmt = _build_format(raw)
    parquet = _build_parquet(raw, "write.parquet")
    target_file_size_bytes = _int(raw.get("write.target-file-size-bytes"))
    manifest = _build_manifest(raw)
    metadata = _build_metadata(raw)
    commit = _build_commit(raw)
    metrics = _build_metrics(raw)
    upsert_enabled = _bool(raw.get("write.upsert.enabled"))
    wap_enabled = _bool(raw.get("write.wap.enabled"))
    object_storage_enabled = _bool(raw.get("write.object-storage.enabled"))

    values = (
        merge,
        update,
        delete,
        distribution_mode,
        fmt,
        parquet,
        target_file_size_bytes,
        manifest,
        metadata,
        commit,
        metrics,
        upsert_enabled,
        wap_enabled,
        object_storage_enabled,
    )
    if all(v is None for v in values):
        return None

    return WriteProperties(
        merge=merge,
        update=update,
        delete=delete,
        distribution_mode=distribution_mode,
        format=fmt,
        parquet=parquet,
        target_file_size_bytes=target_file_size_bytes,
        manifest=manifest,
        metadata=metadata,
        commit=commit,
        metrics=metrics,
        upsert_enabled=upsert_enabled,
        wap_enabled=wap_enabled,
        object_storage_enabled=object_storage_enabled,
    )


def _build_operation(raw: dict[str, str], prefix: str) -> OperationProperties | None:
    mode = _enum(WriteMode, raw.get(f"{prefix}.mode"))
    isolation = _enum(IsolationLevel, raw.get(f"{prefix}.isolation-level"))
    dist = _enum(DistributionMode, raw.get(f"{prefix}.distribution-mode"))
    if all(v is None for v in (mode, isolation, dist)):
        return None
    return OperationProperties(
        mode=mode, isolation_level=isolation, distribution_mode=dist
    )


def _build_delete(raw: dict[str, str]) -> DeleteProperties | None:
    mode = _enum(WriteMode, raw.get("write.delete.mode"))
    isolation = _enum(IsolationLevel, raw.get("write.delete.isolation-level"))
    dist = _enum(DistributionMode, raw.get("write.delete.distribution-mode"))
    format_default = raw.get("write.delete.format.default")
    target = _int(raw.get("write.delete.target-file-size-bytes"))
    parquet = _build_parquet(raw, "write.delete.parquet")
    if all(v is None for v in (mode, isolation, dist, format_default, target, parquet)):
        return None
    return DeleteProperties(
        mode=mode,
        isolation_level=isolation,
        distribution_mode=dist,
        format_default=format_default,
        target_file_size_bytes=target,
        parquet=parquet,
    )


def _build_parquet(raw: dict[str, str], prefix: str) -> ParquetProperties | None:
    codec = raw.get(f"{prefix}.compression-codec")
    level = _int(raw.get(f"{prefix}.compression-level"))
    row_group = _int(raw.get(f"{prefix}.row-group-size-bytes"))
    page = _int(raw.get(f"{prefix}.page-size-bytes"))
    dict_size = _int(raw.get(f"{prefix}.dict-size-bytes"))
    if all(v is None for v in (codec, level, row_group, page, dict_size)):
        return None
    return ParquetProperties(
        compression_codec=codec,
        compression_level=level,
        row_group_size_bytes=row_group,
        page_size_bytes=page,
        dict_size_bytes=dict_size,
    )


def _build_format(raw: dict[str, str]) -> FormatProperties | None:
    default = raw.get("write.format.default")
    if default is None:
        return None
    return FormatProperties(default=default)


def _build_manifest(raw: dict[str, str]) -> ManifestProperties | None:
    target = _int(raw.get("write.manifest.target-size-bytes"))
    min_merge = _int(raw.get("write.manifest.min-merge-count"))
    merge_enabled = _bool(raw.get("write.manifest.merge.enabled"))
    if all(v is None for v in (target, min_merge, merge_enabled)):
        return None
    return ManifestProperties(
        target_size_bytes=target,
        min_merge_count=min_merge,
        merge_enabled=merge_enabled,
    )


def _build_metadata(raw: dict[str, str]) -> MetadataProperties | None:
    codec = raw.get("write.metadata.compression-codec")
    delete_after = _bool(raw.get("write.metadata.delete-after-commit.enabled"))
    prev_max = _int(raw.get("write.metadata.previous-versions-max"))
    if all(v is None for v in (codec, delete_after, prev_max)):
        return None
    return MetadataProperties(
        compression_codec=codec,
        delete_after_commit_enabled=delete_after,
        previous_versions_max=prev_max,
    )


def _build_commit(raw: dict[str, str]) -> CommitProperties | None:
    retries = _int(raw.get("write.commit.num-retries"))
    min_wait = _int(raw.get("write.commit.retry.min-wait-ms"))
    max_wait = _int(raw.get("write.commit.retry.max-wait-ms"))
    total = _int(raw.get("write.commit.retry.total-timeout-ms"))
    if all(v is None for v in (retries, min_wait, max_wait, total)):
        return None
    return CommitProperties(
        num_retries=retries,
        retry_min_wait_ms=min_wait,
        retry_max_wait_ms=max_wait,
        total_retry_time_ms=total,
    )


def _build_metrics(raw: dict[str, str]) -> MetricsProperties | None:
    mode = raw.get("write.metrics.mode")
    if mode is None:
        return None
    return MetricsProperties(default_mode=mode)


# --- Read ---


def _build_read(raw: dict[str, str]) -> ReadProperties | None:
    split = _build_split(raw)
    parquet = _build_read_parquet(raw)
    orc = _build_read_orc(raw)
    if all(v is None for v in (split, parquet, orc)):
        return None
    return ReadProperties(split=split, parquet=parquet, orc=orc)


def _build_split(raw: dict[str, str]) -> SplitProperties | None:
    size = _int(raw.get("read.split.planning.size"))
    lookback = _int(raw.get("read.split.planning.lookback"))
    cost = _int(raw.get("read.split.planning.open-file-cost"))
    if all(v is None for v in (size, lookback, cost)):
        return None
    return SplitProperties(size=size, lookback=lookback, open_file_cost=cost)


def _build_read_parquet(raw: dict[str, str]) -> ReadParquetProperties | None:
    vec = _bool(raw.get("read.parquet.vectorization.enabled"))
    batch = _int(raw.get("read.parquet.batch-size"))
    if all(v is None for v in (vec, batch)):
        return None
    return ReadParquetProperties(vectorization_enabled=vec, batch_size=batch)


def _build_read_orc(raw: dict[str, str]) -> ReadOrcProperties | None:
    vec = _bool(raw.get("read.orc.vectorization.enabled"))
    batch = _int(raw.get("read.orc.batch-size"))
    if all(v is None for v in (vec, batch)):
        return None
    return ReadOrcProperties(vectorization_enabled=vec, batch_size=batch)


# --- Helpers ---


def _int(v: str | None) -> int | None:
    return int(v) if v is not None else None


def _bool(v: str | None) -> bool | None:
    return v.lower() == "true" if v is not None else None


def _enum[T: StrEnum](cls: type[T], v: str | None) -> T | None:
    return cls(v) if v is not None else None
