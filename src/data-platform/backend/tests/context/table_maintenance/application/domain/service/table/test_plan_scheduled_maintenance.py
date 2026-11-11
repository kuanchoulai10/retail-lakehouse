"""Test which operations and partitions scheduled maintenance plans for a table."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation as Op,
)
from context.table_maintenance.application.domain.model.shared import (
    ManifestStats,
    PartitionFieldInfo,
    PartitionSpecInfo,
    PartitionStats,
    SnapshotInfo,
    TableObservation,
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
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    CompactionScope,
    CompactionUnit,
    ExpireSnapshotsExecutionPolicy,
    MaintenancePolicyContent,
    RewriteManifestsConditions,
    RewriteManifestsTriggerPolicy,
    SmallManifestsCondition,
)
from context.table_maintenance.application.domain.service.table import (
    plan_scheduled_maintenance,
)
from tests.context.table_maintenance.fakes.policy_with_only_operation import policy_with_only_operation
from tests.context.table_maintenance.fakes.policy_with_operation import policy_with_operation

NOW = datetime(2026, 10, 24, 12, tzinfo=UTC)
MIB = 1024 * 1024
DEFAULT = MaintenancePolicyContent.platform_default()
DAY_SPEC = PartitionSpecInfo(
    spec_id=0,
    fields=(PartitionFieldInfo(field_id=1000, name="d", source_column="ts", source_type="timestamp", transform="day"),),
)
NO_SPEC = PartitionSpecInfo(spec_id=1, fields=())


def table() -> Table:
    """Build a managed table."""
    return Table.register(
        TableId("u"),
        TableName(catalog="c", namespace="n", table="t"),
        TableDiscoveryRuleId("r"),
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


def compact_only(unit: CompactionUnit = CompactionUnit.PARTITION) -> MaintenancePolicyContent:
    """Return a policy with only data file compaction enabled, over the given unit."""
    return policy_with_operation(
        policy_with_only_operation(Op.REWRITE_DATA_FILES), Op.REWRITE_DATA_FILES, scope=CompactionScope(unit=unit)
    )


def retain_last(policy: MaintenancePolicyContent, n: int) -> MaintenancePolicyContent:
    """Return the policy with snapshot expiry retaining the last ``n`` snapshots."""
    execution = ExpireSnapshotsExecutionPolicy(older_than=timedelta(days=1), retain_last=n)
    return policy_with_operation(policy, Op.EXPIRE_SNAPSHOTS, execution_policy=execution)


P = compact_only()


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
    plan = plan_scheduled_maintenance(table(), compact_only(), o, NOW)
    assert ops(plan) == [Op.REWRITE_DATA_FILES]
    assert plan.operations[0].partitions == (o.partitions[1], o.partitions[2])


def test_table_scope_sums_partitions():
    """With table scope the reducible files of all partitions are summed and the whole table is planned."""
    s = compact_only(CompactionUnit.TABLE)
    o = obs(partitions=(part(2, value=1), part(2, value=2), part(2, value=3)))
    plan = plan_scheduled_maintenance(table(), s, o, NOW)
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
    plan = plan_scheduled_maintenance(table(), compact_only(), o, NOW)
    assert ops(plan) == [Op.REWRITE_DATA_FILES]
    assert plan.operations[0].partitions == ()


def test_unknown_spec_counts_as_unpartitioned():
    """Partitions of an unknown spec are treated as unpartitioned."""
    o = obs(partitions=(part(10, spec_id=99),))
    assert plan_scheduled_maintenance(table(), compact_only(), o, NOW).operations[0].partitions == ()


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
    plan = plan_scheduled_maintenance(table(), compact_only(), o, NOW)
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
    plan = plan_scheduled_maintenance(table(), compact_only(), o, NOW)
    assert plan.operations[0].partitions == o.partitions[:2]


def test_no_partition_over_threshold_plans_nothing():
    """No partition over the threshold plans nothing."""
    assert plan_scheduled_maintenance(table(), compact_only(), obs(partitions=(part(4),)), NOW).is_empty


def test_cooldown_skips_operation():
    """An operation in cooldown is not planned until the cooldown ends."""
    o = obs(partitions=(part(10),))
    t = table()
    t.operation_states[Op.REWRITE_DATA_FILES] = OperationState(last_attempt_at=NOW - timedelta(minutes=30))
    assert plan_scheduled_maintenance(t, P, o, NOW).is_empty
    t.operation_states[Op.REWRITE_DATA_FILES] = OperationState(
        last_attempt_at=NOW - timedelta(hours=3), consecutive_failures=2
    )
    assert plan_scheduled_maintenance(t, P, o, NOW).is_empty
    t.operation_states[Op.REWRITE_DATA_FILES] = OperationState(
        last_attempt_at=NOW - timedelta(hours=5), consecutive_failures=2
    )
    assert not plan_scheduled_maintenance(t, P, o, NOW).is_empty


def test_disabled_operation_never_planned():
    """A disabled operation is never planned."""
    s = policy_with_operation(policy_with_only_operation(Op.REMOVE_ORPHAN_FILES), Op.REMOVE_ORPHAN_FILES, enabled=False)
    assert plan_scheduled_maintenance(table(), s, obs(partitions=(part(10),)), NOW).is_empty


def test_expire_snapshots_due_only_when_something_expires():
    """Snapshot expiry is planned only when some snapshot can expire."""
    s = policy_with_only_operation(Op.EXPIRE_SNAPSHOTS)
    assert ops(plan_scheduled_maintenance(table(), s, obs(snapshots=snaps(12, 11)), NOW)) == [Op.EXPIRE_SNAPSHOTS]
    assert plan_scheduled_maintenance(table(), s, obs(snapshots=snaps(10, 10)), NOW).is_empty


def test_current_snapshot_is_never_expirable():
    """The current snapshot is never counted as expirable."""
    s = retain_last(policy_with_only_operation(Op.EXPIRE_SNAPSHOTS), 1)
    old = (
        SnapshotInfo(snapshot_id=1, committed_at=NOW - timedelta(days=5)),
        SnapshotInfo(snapshot_id=2, committed_at=NOW - timedelta(days=4)),
    )
    assert plan_scheduled_maintenance(table(), s, obs(snapshots=old, current_snapshot_id=1), NOW).is_empty
    assert ops(plan_scheduled_maintenance(table(), s, obs(snapshots=old, current_snapshot_id=2), NOW)) == [
        Op.EXPIRE_SNAPSHOTS
    ]


def test_rewrite_manifests_due_on_small_manifest_count():
    """Manifest rewriting is planned when enough small manifests exist."""
    s = policy_with_only_operation(Op.REWRITE_MANIFESTS)
    small = ManifestStats(length_bytes=MIB)
    big = ManifestStats(length_bytes=9 * MIB)
    assert ops(plan_scheduled_maintenance(table(), s, obs(manifests=(small,) * 5 + (big,)), NOW)) == [
        Op.REWRITE_MANIFESTS
    ]
    assert plan_scheduled_maintenance(table(), s, obs(manifests=(small,) * 4), NOW).is_empty


def test_manifest_threshold_from_settings_and_property():
    """The small manifest threshold comes from the condition and the table property."""
    m = (ManifestStats(length_bytes=2 * MIB),) * 5
    s = policy_with_only_operation(Op.REWRITE_MANIFESTS)
    assert not plan_scheduled_maintenance(table(), s, obs(manifests=m), NOW).is_empty
    prop = obs(manifests=m, properties={"commit.manifest.target-size-bytes": str(MIB)})
    assert plan_scheduled_maintenance(table(), s, prop, NOW).is_empty
    trigger = RewriteManifestsTriggerPolicy(
        cooldown=timedelta(hours=6),
        conditions=RewriteManifestsConditions(
            small_manifests=SmallManifestsCondition(at_least=5, smaller_than_bytes=MIB)
        ),
    )
    s2 = policy_with_operation(s, Op.REWRITE_MANIFESTS, trigger_policy=trigger)
    assert plan_scheduled_maintenance(table(), s2, obs(manifests=m), NOW).is_empty


def test_remove_orphan_files_due_after_interval():
    """Orphan file removal is planned again once its cooldown has passed."""
    s = policy_with_only_operation(Op.REMOVE_ORPHAN_FILES)
    t = table()
    assert ops(plan_scheduled_maintenance(t, s, obs(), NOW)) == [Op.REMOVE_ORPHAN_FILES]
    t.operation_states[Op.REMOVE_ORPHAN_FILES] = OperationState(last_attempt_at=NOW - timedelta(days=6))
    assert plan_scheduled_maintenance(t, s, obs(), NOW).is_empty
    assert DEFAULT.operations.remove_orphan_files.trigger_policy.cooldown == timedelta(days=7)


def test_plan_order_is_canonical():
    """Planned operations follow the canonical order."""
    o = obs(
        partitions=(part(10),),
        manifests=(ManifestStats(length_bytes=MIB),) * 5,
        snapshots=snaps(12, 11),
    )
    assert ops(plan_scheduled_maintenance(table(), DEFAULT, o, NOW)) == list(Op.ordered())


def test_unmanaged_or_dropped_table_yields_empty_plan():
    """An unmanaged or dropped table gets an empty plan."""
    o = obs(partitions=(part(10),))
    unmanaged = table()
    unmanaged.unmanage(NOW)
    assert plan_scheduled_maintenance(unmanaged, DEFAULT, o, NOW).is_empty
    dropped = table()
    dropped.mark_dropped(NOW)
    assert plan_scheduled_maintenance(dropped, DEFAULT, o, NOW).is_empty


def test_cooldown_boundary_is_inclusive():
    """An operation is planned exactly when its cooldown ends."""
    t = table()
    o = obs(partitions=(part(10),))
    t.operation_states[Op.REWRITE_DATA_FILES] = OperationState(last_attempt_at=NOW - timedelta(hours=1))
    assert ops(plan_scheduled_maintenance(t, P, o, NOW)) == [Op.REWRITE_DATA_FILES]


def test_manifest_equal_to_threshold_is_not_small():
    """A manifest exactly at the size threshold is not counted as small."""
    s = policy_with_only_operation(Op.REWRITE_MANIFESTS)
    m = (ManifestStats(length_bytes=8 * MIB),) * 5
    assert plan_scheduled_maintenance(table(), s, obs(manifests=m), NOW).is_empty


def test_snapshot_committed_exactly_at_cutoff_is_not_expirable():
    """A snapshot committed exactly at the cutoff is not expirable."""
    s = retain_last(policy_with_only_operation(Op.EXPIRE_SNAPSHOTS), 1)
    snaps_ = (
        SnapshotInfo(snapshot_id=1, committed_at=NOW - timedelta(days=1)),
        SnapshotInfo(snapshot_id=2, committed_at=NOW),
    )
    assert plan_scheduled_maintenance(table(), s, obs(snapshots=snaps_), NOW).is_empty


def test_table_scope_sum_equal_to_threshold_is_planned():
    """A table scope sum equal to the threshold is planned."""
    s = compact_only(CompactionUnit.TABLE)
    o = obs(partitions=(part(2, value=1), part(3, value=2)))
    assert ops(plan_scheduled_maintenance(table(), s, o, NOW)) == [Op.REWRITE_DATA_FILES]


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
        assert plan_scheduled_maintenance(table(), s, o, NOW).is_empty
    valid = obs(
        properties={"write.target-file-size-bytes": str(500 * 1024 * 1024 * 1024)},
        partitions=ten_files_5gib,
    )
    assert ops(plan_scheduled_maintenance(table(), s, valid, NOW)) == [Op.REWRITE_DATA_FILES]


def test_malformed_manifest_size_property_falls_back_to_default():
    """A malformed manifest size property falls back to the default."""
    s = policy_with_only_operation(Op.REWRITE_MANIFESTS)
    m = (ManifestStats(length_bytes=MIB),) * 5
    for bad in ("abc", "0", "-5"):
        o = obs(properties={"commit.manifest.target-size-bytes": bad}, manifests=m)
        assert ops(plan_scheduled_maintenance(table(), s, o, NOW)) == [Op.REWRITE_MANIFESTS]
