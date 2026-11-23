"""Define the planning inputs whose Spark request the golden file pins."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
    PartitionFieldInfo,
    PartitionSpecInfo,
    PartitionStats,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    AtMost,
    ExpireSnapshotsOptions,
    ExpireSnapshotsSpec,
    ExpireSnapshotsTarget,
    MaintenancePolicyContent,
    PrefixMismatchMode,
    RemoveOrphanFilesOptions,
    RemoveOrphanFilesSpec,
    RemoveOrphanFilesTarget,
    RewriteDataFilesOptions,
    RewriteDataFilesSpec,
    RewriteDataFilesStrategy,
    RewriteDataFilesTarget,
    RewriteManifestsOptions,
    RewriteManifestsSpec,
    RewriteManifestsTarget,
)
from tests.context.table_maintenance.fakes.policy_with_operation import policy_with_operation

OPS = MaintenanceOperation
DEFAULT = MaintenancePolicyContent.platform_default()
NOW = datetime(2026, 10, 24, 12, tzinfo=UTC)
NOW_TAIPEI = datetime(2026, 10, 24, 20, 15, 30, 123456, tzinfo=timezone(timedelta(hours=8)))


@dataclass(frozen=True)
class SparkRequestCase:
    """One planning input: an operation, its policy and table, and the partitions selected."""

    name: str
    operation: MaintenanceOperation
    policy: MaintenancePolicyContent
    properties: dict[str, str]
    now: datetime
    catalog: str = "iceberg"
    specs: tuple[PartitionSpecInfo, ...] = ()
    partitions: tuple[PartitionStats, ...] = ()


def _without(operation: MaintenanceOperation) -> MaintenancePolicyContent:
    return policy_with_operation(DEFAULT, operation, None)


def _field(column: str, source_type: str, transform: str, field_id: int = 1000) -> PartitionFieldInfo:
    return PartitionFieldInfo(
        field_id=field_id, name=column, source_column=column, source_type=source_type, transform=transform
    )


def _spec(spec_id: int, *fields: PartitionFieldInfo) -> PartitionSpecInfo:
    return PartitionSpecInfo(spec_id=spec_id, fields=fields)


def _part(spec_id: int, *values: str | float | bool | None) -> PartitionStats:
    return PartitionStats(
        spec_id=spec_id,
        values=values,
        data_file_count=3,
        position_delete_file_count=0,
        equality_delete_file_count=0,
        total_data_file_size_bytes=1,
    )


_EVERY_OPTION = RewriteDataFilesOptions(
    strategy=RewriteDataFilesStrategy.SORT,
    sort_order="id DESC NULLS LAST, ts",
    min_input_files=4,
    partial_progress_enabled=True,
    partial_progress_max_commits=7,
    max_concurrent_file_group_rewrites=3,
    rewrite_all=False,
    delete_file_threshold=2,
    remove_dangling_deletes=True,
    max_file_group_size_bytes=1073741824,
)
_COMPACT_EVERY_OPTION = policy_with_operation(
    DEFAULT,
    OPS.REWRITE_DATA_FILES,
    RewriteDataFilesSpec(target=RewriteDataFilesTarget(reducible_files=AtMost(at_most=5)), options=_EVERY_OPTION),
)
_REGION = _spec(0, _field("region", "string", "identity"))
_DAY_BUCKET = _spec(0, _field("ts", "timestamptz", "day"), _field("id", "long", "bucket[16]", 1001))
_SCALARS = _spec(
    0,
    _field("name", "string", "truncate[4]"),
    _field("flag", "boolean", "identity", 1001),
    _field("price", "decimal(10, 2)", "identity", 1002),
    _field("score", "double", "identity", 1003),
    _field("seq", "long", "identity", 1004),
    _field("note", "string", "identity", 1005),
)
_TIMES = _spec(
    0,
    _field("d", "date", "month"),
    _field("y", "date", "year", 1001),
    _field("t", "timestamp", "hour", 1002),
)
_NESTED = _spec(0, _field("a.b", "int", "identity"), _field("a.c", "long", "bucket[4]", 1001))

SPARK_REQUEST_CASES: tuple[SparkRequestCase, ...] = (
    SparkRequestCase("compaction_every_option", OPS.REWRITE_DATA_FILES, _COMPACT_EVERY_OPTION, {}, NOW),
    SparkRequestCase("compaction_platform_default", OPS.REWRITE_DATA_FILES, DEFAULT, {}, NOW),
    SparkRequestCase(
        "compaction_left_out_with_table_size",
        OPS.REWRITE_DATA_FILES,
        _without(OPS.REWRITE_DATA_FILES),
        {"write.target-file-size-bytes": "134217728"},
        NOW,
    ),
    SparkRequestCase(
        "compaction_quote_and_backslash",
        OPS.REWRITE_DATA_FILES,
        DEFAULT,
        {},
        NOW,
        specs=(_REGION,),
        partitions=(_part(0, "o'neil"), _part(0, "a\\b")),
    ),
    SparkRequestCase(
        "compaction_day_and_bucket",
        OPS.REWRITE_DATA_FILES,
        DEFAULT,
        {},
        NOW,
        specs=(_DAY_BUCKET,),
        partitions=(_part(0, 20385, 7), _part(0, 20386, 0)),
    ),
    SparkRequestCase(
        "compaction_evolved_spec",
        OPS.REWRITE_DATA_FILES,
        DEFAULT,
        {},
        NOW,
        specs=(_spec(1, _field("ts", "timestamptz", "day")), _REGION),
        partitions=(_part(1, 20385), _part(0, "eu"), _part(1, 20384)),
    ),
    SparkRequestCase(
        "compaction_month_year_hour",
        OPS.REWRITE_DATA_FILES,
        DEFAULT,
        {},
        NOW,
        specs=(_TIMES,),
        partitions=(_part(0, 681, 56, 489240),),
    ),
    SparkRequestCase(
        "compaction_scalar_values_and_null",
        OPS.REWRITE_DATA_FILES,
        DEFAULT,
        {},
        NOW,
        specs=(_SCALARS,),
        partitions=(_part(0, "abcd", True, "12.50", 1.5, 9000000000, None),),
    ),
    SparkRequestCase(
        "compaction_nested_column_and_backtick_catalog",
        OPS.REWRITE_DATA_FILES,
        DEFAULT,
        {},
        NOW,
        catalog="ice`berg",
        specs=(_NESTED,),
        partitions=(_part(0, 3, 1),),
    ),
    SparkRequestCase(
        "manifests_with_caching",
        OPS.REWRITE_MANIFESTS,
        policy_with_operation(
            DEFAULT,
            OPS.REWRITE_MANIFESTS,
            RewriteManifestsSpec(
                target=RewriteManifestsTarget(small_manifests=AtMost(at_most=5)),
                options=RewriteManifestsOptions(use_caching=False),
            ),
        ),
        {},
        NOW,
    ),
    SparkRequestCase("manifests_left_out", OPS.REWRITE_MANIFESTS, _without(OPS.REWRITE_MANIFESTS), {}, NOW),
    SparkRequestCase(
        "expiry_with_options",
        OPS.EXPIRE_SNAPSHOTS,
        policy_with_operation(
            DEFAULT,
            OPS.EXPIRE_SNAPSHOTS,
            ExpireSnapshotsSpec(
                target=ExpireSnapshotsTarget(min_snapshots_to_keep=4, max_snapshot_age=timedelta(days=2)),
                options=ExpireSnapshotsOptions(max_concurrent_deletes=8, stream_results=True),
            ),
        ),
        {},
        NOW_TAIPEI,
    ),
    SparkRequestCase(
        "expiry_left_out_with_table_retention",
        OPS.EXPIRE_SNAPSHOTS,
        _without(OPS.EXPIRE_SNAPSHOTS),
        {"history.expire.min-snapshots-to-keep": "3", "history.expire.max-snapshot-age-ms": "3600000"},
        NOW_TAIPEI,
    ),
    SparkRequestCase(
        "orphans_with_options",
        OPS.REMOVE_ORPHAN_FILES,
        policy_with_operation(
            DEFAULT,
            OPS.REMOVE_ORPHAN_FILES,
            RemoveOrphanFilesSpec(
                target=RemoveOrphanFilesTarget(older_than=timedelta(days=2)),
                options=RemoveOrphanFilesOptions(
                    max_concurrent_deletes=4, prefix_mismatch_mode=PrefixMismatchMode.IGNORE
                ),
            ),
        ),
        {},
        NOW_TAIPEI,
    ),
    SparkRequestCase("orphans_left_out", OPS.REMOVE_ORPHAN_FILES, _without(OPS.REMOVE_ORPHAN_FILES), {}, NOW_TAIPEI),
)
