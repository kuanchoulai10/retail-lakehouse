from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from application.domain.model.discovery_rule import DiscoveryRuleId
from application.domain.model.maintenance import MaintenanceOperation as Op
from application.domain.model.maintenance_settings import (
    CompactionScope,
    ExpireSnapshotsSettings,
    MaintenanceSettings,
    RemoveOrphanFilesSettings,
    RewriteDataFilesSettings,
    RewriteManifestsSettings,
)
from application.domain.model.managed_table import (
    ManagedTable,
    OperationState,
    TableName,
    TableUuid,
)
from application.domain.model.observation import (
    ManifestStats,
    PartitionFieldInfo,
    PartitionSpecInfo,
    PartitionStats,
    SnapshotInfo,
    TableObservation,
)
from application.domain.model.policy_template import PolicyTemplateId
from application.domain.service.plan_scheduled_maintenance import (
    plan_scheduled_maintenance,
)

NOW = datetime(2026, 10, 24, 12, tzinfo=UTC)
MIB = 1024 * 1024
DAY_SPEC = PartitionSpecInfo(
    0, (PartitionFieldInfo(1000, "d", "ts", "timestamp", "day"),)
)
NO_SPEC = PartitionSpecInfo(1, ())


def table(settings=None) -> ManagedTable:
    return ManagedTable.register_auto(
        TableUuid("u"),
        TableName("c", "n", "t"),
        DiscoveryRuleId("r"),
        PolicyTemplateId("t"),
        settings or MaintenanceSettings(),
        NOW - timedelta(days=30),
    )


def part(reducible, spec_id=0, value=0) -> PartitionStats:
    return PartitionStats(spec_id, (value,), reducible, 0, 0, 0)


def obs(
    *,
    properties: dict[str, str] | None = None,
    current_snapshot_id: int | None = None,
    specs: tuple[PartitionSpecInfo, ...] = (DAY_SPEC,),
    partitions: tuple[PartitionStats, ...] = (),
    manifests: tuple[ManifestStats, ...] = (),
    snapshots: tuple[SnapshotInfo, ...] = (),
) -> TableObservation:
    return TableObservation(
        "u",
        properties or {},
        current_snapshot_id,
        specs,
        partitions,
        manifests,
        snapshots,
    )


def ops(plan):
    return [p.operation for p in plan.operations]


def only(settings: MaintenanceSettings, op: Op) -> MaintenanceSettings:
    changes = {}
    for o in Op.ordered():
        name = o.value
        cfg = settings.for_operation(o)
        changes[name] = replace(cfg, enabled=(o == op))
    return replace(settings, **changes)


def compact_only(**kw) -> MaintenanceSettings:
    cfg = RewriteDataFilesSettings(**kw)
    return only(
        replace(MaintenanceSettings(), rewrite_data_files=cfg), Op.REWRITE_DATA_FILES
    )


def snaps(n, old):
    return tuple(
        SnapshotInfo(
            i,
            NOW - (timedelta(days=2, minutes=i) if i < old else timedelta(minutes=i)),
        )
        for i in range(n)
    )


def test_partition_scope_selects_only_partitions_over_threshold():
    o = obs(partitions=(part(2, value=1), part(5, value=2), part(9, value=3)))
    plan = plan_scheduled_maintenance(table(compact_only()), o, NOW)
    assert ops(plan) == [Op.REWRITE_DATA_FILES]
    assert plan.operations[0].partitions == (o.partitions[1], o.partitions[2])


def test_table_scope_sums_partitions():
    s = compact_only(scope=CompactionScope.TABLE)
    o = obs(partitions=(part(2, value=1), part(2, value=2), part(2, value=3)))
    plan = plan_scheduled_maintenance(table(s), o, NOW)
    assert plan.operations[0].operation == Op.REWRITE_DATA_FILES
    assert plan.operations[0].partitions == ()


def test_unpartitioned_table_plans_whole_table():
    o = obs(specs=(NO_SPEC,), partitions=(PartitionStats(1, (), 10, 0, 0, 0),))
    plan = plan_scheduled_maintenance(table(compact_only()), o, NOW)
    assert ops(plan) == [Op.REWRITE_DATA_FILES]
    assert plan.operations[0].partitions == ()


def test_unknown_spec_counts_as_unpartitioned():
    o = obs(partitions=(part(10, spec_id=99),))
    assert (
        plan_scheduled_maintenance(table(compact_only()), o, NOW)
        .operations[0]
        .partitions
        == ()
    )


def test_mixed_specs_with_unpartitioned_selection_plans_whole_table():
    o = obs(
        specs=(DAY_SPEC, NO_SPEC),
        partitions=(part(6, value=1), PartitionStats(1, (), 6, 0, 0, 0)),
    )
    plan = plan_scheduled_maintenance(table(compact_only()), o, NOW)
    assert ops(plan) == [Op.REWRITE_DATA_FILES]
    assert plan.operations[0].partitions == ()


def test_partitions_of_two_partitioned_specs_stay_partition_scoped():
    other = PartitionSpecInfo(
        2, (PartitionFieldInfo(1001, "m", "ts", "timestamp", "month"),)
    )
    o = obs(
        specs=(DAY_SPEC, other),
        partitions=(part(6, value=1), part(6, spec_id=2, value=2), part(1, value=3)),
    )
    plan = plan_scheduled_maintenance(table(compact_only()), o, NOW)
    assert plan.operations[0].partitions == o.partitions[:2]


def test_no_partition_over_threshold_plans_nothing():
    assert plan_scheduled_maintenance(
        table(compact_only()), obs(partitions=(part(4),)), NOW
    ).is_empty


def test_cooldown_skips_operation():
    o = obs(partitions=(part(10),))
    t = table(compact_only())
    t.operation_states[Op.REWRITE_DATA_FILES] = OperationState(
        NOW - timedelta(minutes=30)
    )
    assert plan_scheduled_maintenance(t, o, NOW).is_empty
    t.operation_states[Op.REWRITE_DATA_FILES] = OperationState(
        NOW - timedelta(hours=3), consecutive_failures=2
    )
    assert plan_scheduled_maintenance(t, o, NOW).is_empty
    t.operation_states[Op.REWRITE_DATA_FILES] = OperationState(
        NOW - timedelta(hours=5), consecutive_failures=2
    )
    assert not plan_scheduled_maintenance(t, o, NOW).is_empty


def test_disabled_operation_never_planned():
    s = only(MaintenanceSettings(), Op.REMOVE_ORPHAN_FILES)
    s = replace(s, remove_orphan_files=RemoveOrphanFilesSettings(enabled=False))
    assert plan_scheduled_maintenance(
        table(s), obs(partitions=(part(10),)), NOW
    ).is_empty


def test_expire_snapshots_due_only_when_something_expires():
    s = only(MaintenanceSettings(), Op.EXPIRE_SNAPSHOTS)
    assert ops(
        plan_scheduled_maintenance(table(s), obs(snapshots=snaps(12, 11)), NOW)
    ) == [Op.EXPIRE_SNAPSHOTS]
    assert plan_scheduled_maintenance(
        table(s), obs(snapshots=snaps(10, 10)), NOW
    ).is_empty


def test_current_snapshot_is_never_expirable():
    s = only(MaintenanceSettings(), Op.EXPIRE_SNAPSHOTS)
    s = replace(s, expire_snapshots=ExpireSnapshotsSettings(retain_last=1))
    old = (
        SnapshotInfo(1, NOW - timedelta(days=5)),
        SnapshotInfo(2, NOW - timedelta(days=4)),
    )
    assert plan_scheduled_maintenance(
        table(s), obs(snapshots=old, current_snapshot_id=1), NOW
    ).is_empty
    assert ops(
        plan_scheduled_maintenance(
            table(s), obs(snapshots=old, current_snapshot_id=2), NOW
        )
    ) == [Op.EXPIRE_SNAPSHOTS]


def test_rewrite_manifests_due_on_small_manifest_count():
    s = only(MaintenanceSettings(), Op.REWRITE_MANIFESTS)
    small = ManifestStats(MIB)
    big = ManifestStats(9 * MIB)
    assert ops(
        plan_scheduled_maintenance(table(s), obs(manifests=(small,) * 5 + (big,)), NOW)
    ) == [Op.REWRITE_MANIFESTS]
    assert plan_scheduled_maintenance(
        table(s), obs(manifests=(small,) * 4), NOW
    ).is_empty


def test_manifest_threshold_from_settings_and_property():
    m = (ManifestStats(2 * MIB),) * 5
    s = only(MaintenanceSettings(), Op.REWRITE_MANIFESTS)
    assert not plan_scheduled_maintenance(table(s), obs(manifests=m), NOW).is_empty
    prop = obs(manifests=m, properties={"commit.manifest.target-size-bytes": str(MIB)})
    assert plan_scheduled_maintenance(table(s), prop, NOW).is_empty
    s2 = replace(
        s, rewrite_manifests=RewriteManifestsSettings(small_manifest_bytes=MIB)
    )
    assert plan_scheduled_maintenance(table(s2), obs(manifests=m), NOW).is_empty


def test_remove_orphan_files_due_after_interval():
    s = only(MaintenanceSettings(), Op.REMOVE_ORPHAN_FILES)
    t = table(s)
    assert ops(plan_scheduled_maintenance(t, obs(), NOW)) == [Op.REMOVE_ORPHAN_FILES]
    t.operation_states[Op.REMOVE_ORPHAN_FILES] = OperationState(NOW - timedelta(days=6))
    assert plan_scheduled_maintenance(t, obs(), NOW).is_empty
    assert RemoveOrphanFilesSettings().min_interval == timedelta(days=7)


def test_plan_order_is_canonical():
    o = obs(
        partitions=(part(10),),
        manifests=(ManifestStats(MIB),) * 5,
        snapshots=snaps(12, 11),
    )
    assert ops(plan_scheduled_maintenance(table(), o, NOW)) == list(Op.ordered())


def test_paused_excluded_or_settingless_table_yields_empty_plan():
    o = obs(partitions=(part(10),))
    paused = table()
    paused.pause(NOW)
    assert plan_scheduled_maintenance(paused, o, NOW).is_empty
    excluded = ManagedTable.exclude_manual(
        TableUuid("u"), TableName("c", "n", "t"), NOW
    )
    assert plan_scheduled_maintenance(excluded, o, NOW).is_empty
    dropped = table()
    dropped.mark_dropped(NOW)
    assert plan_scheduled_maintenance(dropped, o, NOW).is_empty


def test_cooldown_boundary_is_inclusive():
    t = table(compact_only())
    o = obs(partitions=(part(10),))
    t.operation_states[Op.REWRITE_DATA_FILES] = OperationState(NOW - timedelta(hours=1))
    assert ops(plan_scheduled_maintenance(t, o, NOW)) == [Op.REWRITE_DATA_FILES]


def test_manifest_equal_to_threshold_is_not_small():
    s = only(MaintenanceSettings(), Op.REWRITE_MANIFESTS)
    m = (ManifestStats(8 * MIB),) * 5
    assert plan_scheduled_maintenance(table(s), obs(manifests=m), NOW).is_empty


def test_snapshot_committed_exactly_at_cutoff_is_not_expirable():
    s = only(MaintenanceSettings(), Op.EXPIRE_SNAPSHOTS)
    s = replace(s, expire_snapshots=ExpireSnapshotsSettings(retain_last=1))
    snaps_ = (SnapshotInfo(1, NOW - timedelta(days=1)), SnapshotInfo(2, NOW))
    assert plan_scheduled_maintenance(table(s), obs(snapshots=snaps_), NOW).is_empty


def test_table_scope_sum_equal_to_threshold_is_planned():
    s = compact_only(scope=CompactionScope.TABLE)
    o = obs(partitions=(part(2, value=1), part(3, value=2)))
    assert ops(plan_scheduled_maintenance(table(s), o, NOW)) == [Op.REWRITE_DATA_FILES]


def test_malformed_target_file_size_property_falls_back_to_default():
    s = compact_only()
    ten_files_5gib = (PartitionStats(0, (1,), 10, 0, 0, 5 * 1024 * MIB),)
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
    assert ops(plan_scheduled_maintenance(table(s), valid, NOW)) == [
        Op.REWRITE_DATA_FILES
    ]


def test_malformed_manifest_size_property_falls_back_to_default():
    s = only(MaintenanceSettings(), Op.REWRITE_MANIFESTS)
    m = (ManifestStats(MIB),) * 5
    for bad in ("abc", "0", "-5"):
        o = obs(properties={"commit.manifest.target-size-bytes": bad}, manifests=m)
        assert ops(plan_scheduled_maintenance(table(s), o, NOW)) == [
            Op.REWRITE_MANIFESTS
        ]
