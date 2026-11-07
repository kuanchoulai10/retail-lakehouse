"""Test the assessment of whether each maintenance operation is due for a table."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from context.table_maintenance.application.domain.model.shared import (
    CompactionScope,
    ExpireSnapshotsSettings,
    MaintenanceSettings,
    ManifestStats,
    OperationAssessment,
    OperationVerdict,
    PartitionFieldInfo,
    PartitionSpecInfo,
    PartitionStats,
    RemoveOrphanFilesSettings,
    RewriteDataFilesSettings,
    SizeSource,
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
    assess_maintenance,
    plan_scheduled_maintenance,
)

NOW = datetime(2026, 10, 24, 12, tzinfo=UTC)
MIB = 1024 * 1024
DAY_SPEC = PartitionSpecInfo(0, (PartitionFieldInfo(1000, "d", "ts", "timestamp", "day"),))


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
    """Build a table observation from the given properties, snapshots, specs and partitions."""
    return TableObservation(
        "u",
        properties or {},
        current_snapshot_id,
        specs,
        partitions,
        manifests,
        snapshots,
    )


def snaps(n, old):
    """Build snapshots of which the given number are old."""
    return tuple(
        SnapshotInfo(
            i,
            NOW - (timedelta(days=2, minutes=i) if i < old else timedelta(minutes=i)),
        )
        for i in range(n)
    )


def assess(t: Table, o: TableObservation, op: Op) -> OperationAssessment:
    """Assess the table and return the assessment of one operation."""
    assert t.settings is not None
    assessment = assess_maintenance(t, t.settings, o, NOW)
    assert [a.operation for a in assessment.operations] == list(Op.ordered())
    return next(a for a in assessment.operations if a.operation == op)


def compaction(**kw) -> MaintenanceSettings:
    """Build settings with the given data file compaction overrides."""
    return replace(MaintenanceSettings(), rewrite_data_files=RewriteDataFilesSettings(**kw))


TWO_PARTITIONS = (part(6, value=1), part(2, value=2))


def test_partition_scope_counts_qualifying_partitions():
    """With partition scope, the measure counts the partitions that qualify for compaction."""
    s = compaction(min_reducible_files=5)
    a = assess(table(s), obs(partitions=TWO_PARTITIONS), Op.REWRITE_DATA_FILES)
    assert a.verdict == OperationVerdict.DUE
    assert a.measured == 6
    assert a.qualifying_partitions == 1
    assert a.threshold == 5
    assert a.planned is not None
    assert a.planned.partitions == TWO_PARTITIONS[:1]


def test_table_scope_sums_every_partition():
    """With table scope, the measure sums the reducible files of every partition."""
    s = compaction(scope=CompactionScope.TABLE, min_reducible_files=5)
    a = assess(table(s), obs(partitions=TWO_PARTITIONS), Op.REWRITE_DATA_FILES)
    assert a.verdict == OperationVerdict.DUE
    assert a.measured == 8
    assert a.qualifying_partitions is None


@pytest.mark.parametrize(
    ("settings_size", "properties", "expected"),
    [
        (1024, {}, (1024, SizeSource.SETTINGS)),
        (
            None,
            {"write.target-file-size-bytes": "2048"},
            (2048, SizeSource.TABLE_PROPERTY),
        ),
        (None, {}, (536870912, SizeSource.DEFAULT)),
    ],
)
def test_target_size_source(settings_size, properties, expected):
    """The target file size comes from the settings, the table property or the default, and its source is reported."""
    s = compaction(target_file_size_bytes=settings_size)
    a = assess(table(s), obs(properties=properties), Op.REWRITE_DATA_FILES)
    assert (a.size_bytes, a.size_source) == expected


def test_manifest_size_source():
    """The manifest size is taken from the table property or the default, and its source is reported."""
    o = obs(
        properties={"commit.manifest.target-size-bytes": str(MIB)},
        manifests=(ManifestStats(MIB // 2),) * 2,
    )
    a = assess(table(), o, Op.REWRITE_MANIFESTS)
    assert (a.size_bytes, a.size_source) == (MIB, SizeSource.TABLE_PROPERTY)
    assert (a.measured, a.threshold, a.verdict) == (2, 5, OperationVerdict.NOT_DUE)
    d = assess(table(), obs(), Op.REWRITE_MANIFESTS)
    assert (d.size_bytes, d.size_source) == (8 * MIB, SizeSource.DEFAULT)


def test_expire_snapshots_counts_expirable():
    """The snapshot expiry measure counts the snapshots that can be expired."""

    def with_retain(n: int) -> MaintenanceSettings:
        return replace(
            MaintenanceSettings(),
            expire_snapshots=ExpireSnapshotsSettings(retain_last=n),
        )

    o = obs(snapshots=snaps(14, 14))
    a = assess(table(with_retain(10)), o, Op.EXPIRE_SNAPSHOTS)
    assert (a.measured, a.threshold, a.verdict) == (4, 1, OperationVerdict.DUE)
    b = assess(table(with_retain(20)), o, Op.EXPIRE_SNAPSHOTS)
    assert (b.measured, b.verdict) == (0, OperationVerdict.NOT_DUE)
    assert b.planned is None


def test_cooldown_reports_next_eligible_time():
    """An operation in cooldown reports when it is next eligible and has no plan."""
    t = table(compaction())
    t.operation_states[Op.REWRITE_DATA_FILES] = OperationState(NOW - timedelta(minutes=30))
    a = assess(t, obs(partitions=(part(10),)), Op.REWRITE_DATA_FILES)
    assert a.verdict == OperationVerdict.COOLDOWN
    assert a.next_eligible_at == NOW + timedelta(minutes=30)
    assert a.planned is None
    assert a.measured == 10


def test_disabled_operation_has_no_measures():
    """A disabled operation reports no measure and no eligibility time."""
    s = replace(
        compaction(enabled=False),
        remove_orphan_files=RemoveOrphanFilesSettings(enabled=False),
    )
    t = table(s)
    t.operation_states[Op.REMOVE_ORPHAN_FILES] = OperationState(NOW)
    a = assess(t, obs(), Op.REMOVE_ORPHAN_FILES)
    assert a.verdict == OperationVerdict.DISABLED
    assert a.measured is None
    assert a.next_eligible_at is None
    c = assess(t, obs(partitions=(part(10),)), Op.REWRITE_DATA_FILES)
    assert c.verdict == OperationVerdict.DISABLED
    assert (c.measured, c.threshold, c.size_bytes, c.size_source) == (
        None,
        None,
        None,
        None,
    )


def test_assessment_ignores_status():
    """The assessment does not depend on the table status, unlike the plan."""
    t = table(compaction())
    t.pause(NOW)
    o = obs(partitions=(part(10),))
    assert assess(t, o, Op.REWRITE_DATA_FILES).verdict == OperationVerdict.DUE
    assert plan_scheduled_maintenance(t, o, NOW).is_empty


def test_plan_equals_due_operations():
    """The plan of an assessment equals the plan of scheduled maintenance."""
    t = table()
    t.operation_states[Op.REWRITE_MANIFESTS] = OperationState(NOW - timedelta(minutes=10))
    o = obs(
        partitions=(part(10, value=1), part(1, value=2)),
        manifests=(ManifestStats(MIB),) * 5,
        snapshots=snaps(12, 11),
    )
    assert t.settings is not None
    assessment = assess_maintenance(t, t.settings, o, NOW)
    assert [a.verdict for a in assessment.operations] == [
        OperationVerdict.DUE,
        OperationVerdict.COOLDOWN,
        OperationVerdict.DUE,
        OperationVerdict.DUE,
    ]
    assert assessment.plan() == plan_scheduled_maintenance(t, o, NOW)
