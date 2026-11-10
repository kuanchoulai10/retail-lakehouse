"""Test which operations and partitions scheduled maintenance plans for a table."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from base.model import validated_copy
from context.table_maintenance.application.domain.model.shared import (
    CompactionScope,
    ExpireSnapshotsSettings,
    MaintenanceSettings,
    ManifestStats,
    PartitionFieldInfo,
    PartitionSpecInfo,
    PartitionStats,
    RemoveOrphanFilesSettings,
    RewriteDataFilesSettings,
    RewriteManifestsSettings,
    SnapshotInfo,
    TableObservation,
)
from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation as Op,
)
from context.table_maintenance.application.domain.model.table import (
    OperationState,
    Table,
    TableId,
    TableName,
)
from context.table_maintenance.application.domain.model.table_discovery_rule import (
    TableDiscoveryRuleId,
)
from context.table_maintenance.application.domain.model.table_maintenance_preset import (
    TableMaintenancePresetId,
)
from context.table_maintenance.application.domain.service.table import (
    plan_scheduled_maintenance,
)

NOW = datetime(2026, 10, 24, 12, tzinfo=UTC)
MIB = 1024 * 1024
DAY_SPEC = PartitionSpecInfo(
    spec_id=0,
    fields=(PartitionFieldInfo(field_id=1000, name="d", source_column="ts", source_type="timestamp", transform="day"),),
)
NO_SPEC = PartitionSpecInfo(spec_id=1, fields=())


def table(settings=None) -> Table:
    """Build an active auto table with the given settings."""
    return Table.register_auto(
        TableId("u"),
        TableName("c", "n", "t"),
        TableDiscoveryRuleId("r"),
        TableMaintenancePresetId("t"),
        settings or MaintenanceSettings(),
        NOW - timedelta(days=30),
    )


def part(reducible, spec_id=0, value=0) -> PartitionStats:
    """Build partition stats with the given reducible file count."""
    return PartitionStats(
        spec_id=spec_id,
        values=(value,),
        data_file_count=reducible,
        position_delete_file_count=0,
        equality_delete_file_count=0,
        total_data_file_size_bytes=0,
    )


def obs(
    *,
    properties: dict[str, str] | None = None,
    current_snapshot_id: int | None = None,
    specs: tuple[PartitionSpecInfo, ...] = (DAY_SPEC,),
    partitions: tuple[PartitionStats, ...] = (),
    manifests: tuple[ManifestStats, ...] = (),
    snapshots: tuple[SnapshotInfo, ...] = (),
) -> TableObservation:
    """Build a table observation from the given properties, snapshots, manifests and partitions."""
    return TableObservation(
        table_uuid="u",
        properties=properties or {},
        current_snapshot_id=current_snapshot_id,
        specs=specs,
        partitions=partitions,
        manifests=manifests,
        snapshots=snapshots,
    )


def ops(plan):
    """Return the operations of a plan."""
    return [p.operation for p in plan.operations]


def only(settings: MaintenanceSettings, op: Op) -> MaintenanceSettings:
    """Return the settings with every operation disabled except the given one."""
    changes = {}
    for o in Op.ordered():
        name = o.value
        cfg = settings.for_operation(o)
        changes[name] = validated_copy(cfg, enabled=(o == op))
    return validated_copy(settings, **changes)


def compact_only(**kw) -> MaintenanceSettings:
    """Return settings with only data file compaction enabled, using the given overrides."""
    cfg = RewriteDataFilesSettings(**kw)
    return only(validated_copy(MaintenanceSettings(), rewrite_data_files=cfg), Op.REWRITE_DATA_FILES)


def snaps(n, old):
    """Build snapshots of which the given number are old."""
    return tuple(
        SnapshotInfo(
            snapshot_id=i, committed_at=NOW - (timedelta(days=2, minutes=i) if i < old else timedelta(minutes=i))
        )
        for i in range(n)
    )


def test_partition_scope_selects_only_partitions_over_threshold():
    """With partition scope only the partitions over the threshold are planned for compaction."""
    o = obs(partitions=(part(2, value=1), part(5, value=2), part(9, value=3)))
    plan = plan_scheduled_maintenance(table(compact_only()), o, NOW)
    assert ops(plan) == [Op.REWRITE_DATA_FILES]
    assert plan.operations[0].partitions == (o.partitions[1], o.partitions[2])


def test_table_scope_sums_partitions():
    """With table scope the reducible files of all partitions are summed and the whole table is planned."""
    s = compact_only(scope=CompactionScope.TABLE)
    o = obs(partitions=(part(2, value=1), part(2, value=2), part(2, value=3)))
    plan = plan_scheduled_maintenance(table(s), o, NOW)
    assert plan.operations[0].operation == Op.REWRITE_DATA_FILES
    assert plan.operations[0].partitions == ()


def test_unpartitioned_table_plans_whole_table():
    """An unpartitioned table is compacted as a whole."""
    o = obs(
        specs=(NO_SPEC,),
        partitions=(
            PartitionStats(
                spec_id=1,
                values=(),
                data_file_count=10,
                position_delete_file_count=0,
                equality_delete_file_count=0,
                total_data_file_size_bytes=0,
            ),
        ),
    )
    plan = plan_scheduled_maintenance(table(compact_only()), o, NOW)
    assert ops(plan) == [Op.REWRITE_DATA_FILES]
    assert plan.operations[0].partitions == ()


def test_unknown_spec_counts_as_unpartitioned():
    """Partitions of an unknown spec are treated as unpartitioned."""
    o = obs(partitions=(part(10, spec_id=99),))
    assert plan_scheduled_maintenance(table(compact_only()), o, NOW).operations[0].partitions == ()


def test_mixed_specs_with_unpartitioned_selection_plans_whole_table():
    """When the selection includes an unpartitioned spec the whole table is planned."""
    o = obs(
        specs=(DAY_SPEC, NO_SPEC),
        partitions=(
            part(6, value=1),
            PartitionStats(
                spec_id=1,
                values=(),
                data_file_count=6,
                position_delete_file_count=0,
                equality_delete_file_count=0,
                total_data_file_size_bytes=0,
            ),
        ),
    )
    plan = plan_scheduled_maintenance(table(compact_only()), o, NOW)
    assert ops(plan) == [Op.REWRITE_DATA_FILES]
    assert plan.operations[0].partitions == ()


def test_partitions_of_two_partitioned_specs_stay_partition_scoped():
    """Partitions of two partitioned specs stay partition scoped."""
    other = PartitionSpecInfo(
        spec_id=2,
        fields=(
            PartitionFieldInfo(field_id=1001, name="m", source_column="ts", source_type="timestamp", transform="month"),
        ),
    )
    o = obs(
        specs=(DAY_SPEC, other),
        partitions=(part(6, value=1), part(6, spec_id=2, value=2), part(1, value=3)),
    )
    plan = plan_scheduled_maintenance(table(compact_only()), o, NOW)
    assert plan.operations[0].partitions == o.partitions[:2]


def test_no_partition_over_threshold_plans_nothing():
    """No partition over the threshold plans nothing."""
    assert plan_scheduled_maintenance(table(compact_only()), obs(partitions=(part(4),)), NOW).is_empty


def test_cooldown_skips_operation():
    """An operation in cooldown is not planned until the cooldown ends."""
    o = obs(partitions=(part(10),))
    t = table(compact_only())
    t.operation_states[Op.REWRITE_DATA_FILES] = OperationState(NOW - timedelta(minutes=30))
    assert plan_scheduled_maintenance(t, o, NOW).is_empty
    t.operation_states[Op.REWRITE_DATA_FILES] = OperationState(NOW - timedelta(hours=3), consecutive_failures=2)
    assert plan_scheduled_maintenance(t, o, NOW).is_empty
    t.operation_states[Op.REWRITE_DATA_FILES] = OperationState(NOW - timedelta(hours=5), consecutive_failures=2)
    assert not plan_scheduled_maintenance(t, o, NOW).is_empty


def test_disabled_operation_never_planned():
    """A disabled operation is never planned."""
    s = only(MaintenanceSettings(), Op.REMOVE_ORPHAN_FILES)
    s = validated_copy(s, remove_orphan_files=RemoveOrphanFilesSettings(enabled=False))
    assert plan_scheduled_maintenance(table(s), obs(partitions=(part(10),)), NOW).is_empty


def test_expire_snapshots_due_only_when_something_expires():
    """Snapshot expiry is planned only when some snapshot can expire."""
    s = only(MaintenanceSettings(), Op.EXPIRE_SNAPSHOTS)
    assert ops(plan_scheduled_maintenance(table(s), obs(snapshots=snaps(12, 11)), NOW)) == [Op.EXPIRE_SNAPSHOTS]
    assert plan_scheduled_maintenance(table(s), obs(snapshots=snaps(10, 10)), NOW).is_empty


def test_current_snapshot_is_never_expirable():
    """The current snapshot is never counted as expirable."""
    s = only(MaintenanceSettings(), Op.EXPIRE_SNAPSHOTS)
    s = validated_copy(s, expire_snapshots=ExpireSnapshotsSettings(retain_last=1))
    old = (
        SnapshotInfo(snapshot_id=1, committed_at=NOW - timedelta(days=5)),
        SnapshotInfo(snapshot_id=2, committed_at=NOW - timedelta(days=4)),
    )
    assert plan_scheduled_maintenance(table(s), obs(snapshots=old, current_snapshot_id=1), NOW).is_empty
    assert ops(plan_scheduled_maintenance(table(s), obs(snapshots=old, current_snapshot_id=2), NOW)) == [
        Op.EXPIRE_SNAPSHOTS
    ]


def test_rewrite_manifests_due_on_small_manifest_count():
    """Manifest rewriting is planned when enough small manifests exist."""
    s = only(MaintenanceSettings(), Op.REWRITE_MANIFESTS)
    small = ManifestStats(length_bytes=MIB)
    big = ManifestStats(length_bytes=9 * MIB)
    assert ops(plan_scheduled_maintenance(table(s), obs(manifests=(small,) * 5 + (big,)), NOW)) == [
        Op.REWRITE_MANIFESTS
    ]
    assert plan_scheduled_maintenance(table(s), obs(manifests=(small,) * 4), NOW).is_empty


def test_manifest_threshold_from_settings_and_property():
    """The small manifest threshold comes from the settings and the table property."""
    m = (ManifestStats(length_bytes=2 * MIB),) * 5
    s = only(MaintenanceSettings(), Op.REWRITE_MANIFESTS)
    assert not plan_scheduled_maintenance(table(s), obs(manifests=m), NOW).is_empty
    prop = obs(manifests=m, properties={"commit.manifest.target-size-bytes": str(MIB)})
    assert plan_scheduled_maintenance(table(s), prop, NOW).is_empty
    s2 = validated_copy(s, rewrite_manifests=RewriteManifestsSettings(small_manifest_bytes=MIB))
    assert plan_scheduled_maintenance(table(s2), obs(manifests=m), NOW).is_empty


def test_remove_orphan_files_due_after_interval():
    """Orphan file removal is planned again once its minimum interval has passed."""
    s = only(MaintenanceSettings(), Op.REMOVE_ORPHAN_FILES)
    t = table(s)
    assert ops(plan_scheduled_maintenance(t, obs(), NOW)) == [Op.REMOVE_ORPHAN_FILES]
    t.operation_states[Op.REMOVE_ORPHAN_FILES] = OperationState(NOW - timedelta(days=6))
    assert plan_scheduled_maintenance(t, obs(), NOW).is_empty
    assert RemoveOrphanFilesSettings().min_interval == timedelta(days=7)


def test_plan_order_is_canonical():
    """Planned operations follow the canonical order."""
    o = obs(
        partitions=(part(10),),
        manifests=(ManifestStats(length_bytes=MIB),) * 5,
        snapshots=snaps(12, 11),
    )
    assert ops(plan_scheduled_maintenance(table(), o, NOW)) == list(Op.ordered())


def test_paused_excluded_or_settingless_table_yields_empty_plan():
    """A paused, excluded or dropped table gets an empty plan."""
    o = obs(partitions=(part(10),))
    paused = table()
    paused.pause(NOW)
    assert plan_scheduled_maintenance(paused, o, NOW).is_empty
    excluded = Table.exclude_manual(TableId("u"), TableName("c", "n", "t"), NOW)
    assert plan_scheduled_maintenance(excluded, o, NOW).is_empty
    dropped = table()
    dropped.mark_dropped(NOW)
    assert plan_scheduled_maintenance(dropped, o, NOW).is_empty


def test_cooldown_boundary_is_inclusive():
    """An operation is planned exactly when its cooldown ends."""
    t = table(compact_only())
    o = obs(partitions=(part(10),))
    t.operation_states[Op.REWRITE_DATA_FILES] = OperationState(NOW - timedelta(hours=1))
    assert ops(plan_scheduled_maintenance(t, o, NOW)) == [Op.REWRITE_DATA_FILES]


def test_manifest_equal_to_threshold_is_not_small():
    """A manifest exactly at the size threshold is not counted as small."""
    s = only(MaintenanceSettings(), Op.REWRITE_MANIFESTS)
    m = (ManifestStats(length_bytes=8 * MIB),) * 5
    assert plan_scheduled_maintenance(table(s), obs(manifests=m), NOW).is_empty


def test_snapshot_committed_exactly_at_cutoff_is_not_expirable():
    """A snapshot committed exactly at the cutoff is not expirable."""
    s = only(MaintenanceSettings(), Op.EXPIRE_SNAPSHOTS)
    s = validated_copy(s, expire_snapshots=ExpireSnapshotsSettings(retain_last=1))
    snaps_ = (
        SnapshotInfo(snapshot_id=1, committed_at=NOW - timedelta(days=1)),
        SnapshotInfo(snapshot_id=2, committed_at=NOW),
    )
    assert plan_scheduled_maintenance(table(s), obs(snapshots=snaps_), NOW).is_empty


def test_table_scope_sum_equal_to_threshold_is_planned():
    """A table scope sum equal to the threshold is planned."""
    s = compact_only(scope=CompactionScope.TABLE)
    o = obs(partitions=(part(2, value=1), part(3, value=2)))
    assert ops(plan_scheduled_maintenance(table(s), o, NOW)) == [Op.REWRITE_DATA_FILES]


def test_malformed_target_file_size_property_falls_back_to_default():
    """A malformed target file size property falls back to the default."""
    s = compact_only()
    ten_files_5gib = (
        PartitionStats(
            spec_id=0,
            values=(1,),
            data_file_count=10,
            position_delete_file_count=0,
            equality_delete_file_count=0,
            total_data_file_size_bytes=5 * 1024 * MIB,
        ),
    )
    for bad in ("abc", "0", "-5"):
        o = obs(
            properties={"write.target-file-size-bytes": bad},
            partitions=ten_files_5gib,
        )
        assert plan_scheduled_maintenance(table(s), o, NOW).is_empty
    valid = obs(
        properties={"write.target-file-size-bytes": str(500 * 1024 * 1024 * 1024)},
        partitions=ten_files_5gib,
    )
    assert ops(plan_scheduled_maintenance(table(s), valid, NOW)) == [Op.REWRITE_DATA_FILES]


def test_malformed_manifest_size_property_falls_back_to_default():
    """A malformed manifest size property falls back to the default."""
    s = only(MaintenanceSettings(), Op.REWRITE_MANIFESTS)
    m = (ManifestStats(length_bytes=MIB),) * 5
    for bad in ("abc", "0", "-5"):
        o = obs(properties={"commit.manifest.target-size-bytes": bad}, manifests=m)
        assert ops(plan_scheduled_maintenance(table(s), o, NOW)) == [Op.REWRITE_MANIFESTS]
