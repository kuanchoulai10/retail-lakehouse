"""Test the assessment of whether each maintenance operation is due for a table."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation as Op,
)
from context.table_maintenance.application.domain.model.shared import (
    ManifestStats,
    Measurement,
    MeasurementComparison,
    MeasurementUnit,
    OperationAssessment,
    OperationVerdict,
    PartitionFieldInfo,
    PartitionSpecInfo,
    PartitionStats,
    SizeSource,
    SnapshotInfo,
    TableObservation,
)
from context.table_maintenance.application.domain.model.table import (
    AppliedPolicyRef,
    AttentionMark,
    OperationState,
    Table,
    TableId,
    TableName,
)
from context.table_maintenance.application.domain.model.table_discovery_rules import (
    TableDiscoveryRuleId,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    AtLeast,
    CompactionScope,
    CompactionUnit,
    ExpireSnapshotsConditions,
    ExpireSnapshotsExecutionPolicy,
    ExpireSnapshotsTriggerPolicy,
    MaintenancePolicyContent,
    PartialProgress,
    RewriteDataFilesConditions,
    RewriteDataFilesExecutionPolicy,
    RewriteDataFilesTriggerPolicy,
    RewriteManifestsConditions,
    RewriteManifestsTriggerPolicy,
    SmallManifestsCondition,
)
from context.table_maintenance.application.domain.service.table import (
    any_condition_holds,
    assess_maintenance,
)
from tests.context.table_maintenance.fakes.policy_with_operation import policy_with_operation

NOW = datetime(2026, 10, 24, 12, tzinfo=UTC)
MIB = 1024 * 1024
DEFAULT = MaintenancePolicyContent.platform_default()
DAY_SPEC = PartitionSpecInfo(
    spec_id=0,
    fields=(PartitionFieldInfo(field_id=1000, name="d", source_column="ts", source_type="timestamp", transform="day"),),
)


def table() -> Table:
    """Build a managed table."""
    return Table.register(
        TableId("u"),
        TableName(catalog="c", namespace="n", table="t"),
        TableDiscoveryRuleId("r"),
        NOW - timedelta(days=30),
    )


def part(reducible, spec_id=0, value=0, size=0) -> PartitionStats:
    """Build partition stats with the given reducible file count."""
    return PartitionStats(
        spec_id=spec_id,
        values=(value,),
        data_file_count=reducible,
        position_delete_file_count=0,
        equality_delete_file_count=0,
        total_data_file_size_bytes=size,
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
    """Build a table observation from the given properties, snapshots, specs and partitions."""
    return TableObservation(
        table_uuid="u",
        properties=properties or {},
        current_snapshot_id=current_snapshot_id,
        specs=specs,
        partitions=partitions,
        manifests=manifests,
        snapshots=snapshots,
    )


def snaps(n, old):
    """Build snapshots of which the given number are old."""
    return tuple(
        SnapshotInfo(
            snapshot_id=i, committed_at=NOW - (timedelta(days=2, minutes=i) if i < old else timedelta(minutes=i))
        )
        for i in range(n)
    )


def assess(t: Table, o: TableObservation, op: Op, policy: MaintenancePolicyContent = DEFAULT) -> OperationAssessment:
    """Assess the table and return the assessment of one operation."""
    assessment = assess_maintenance(t, policy, o, NOW)
    assert [a.operation for a in assessment.operations] == list(Op.ordered())
    return next(a for a in assessment.operations if a.operation == op)


def compaction(
    *,
    at_least: int | None = 5,
    unit: CompactionUnit = CompactionUnit.PARTITION,
    enabled: bool = True,
    target_file_size_bytes: int | None = None,
) -> MaintenancePolicyContent:
    """Build a policy with the given data file compaction values."""
    return policy_with_operation(
        DEFAULT,
        Op.REWRITE_DATA_FILES,
        enabled=enabled,
        scope=CompactionScope(unit=unit),
        trigger_policy=RewriteDataFilesTriggerPolicy(
            cooldown=timedelta(hours=1),
            conditions=RewriteDataFilesConditions(
                reducible_files=None if at_least is None else AtLeast(at_least=at_least)
            ),
        ),
        execution_policy=RewriteDataFilesExecutionPolicy(
            target_file_size_bytes=target_file_size_bytes,
            min_input_files=2,
            partial_progress=PartialProgress(enabled=True),
        ),
    )


def manifests(*, at_least: int = 5, smaller_than_bytes: int | None = None) -> MaintenancePolicyContent:
    """Build a policy with the given small manifests condition."""
    return policy_with_operation(
        DEFAULT,
        Op.REWRITE_MANIFESTS,
        trigger_policy=RewriteManifestsTriggerPolicy(
            cooldown=timedelta(hours=6),
            conditions=RewriteManifestsConditions(
                small_manifests=SmallManifestsCondition(at_least=at_least, smaller_than_bytes=smaller_than_bytes)
            ),
        ),
    )


def snapshots(*, retain_last: int = 10, at_least: int | None = 1) -> MaintenancePolicyContent:
    """Build a policy with the given snapshot expiry values."""
    return policy_with_operation(
        DEFAULT,
        Op.EXPIRE_SNAPSHOTS,
        trigger_policy=ExpireSnapshotsTriggerPolicy(
            cooldown=timedelta(hours=6),
            conditions=ExpireSnapshotsConditions(
                expirable_snapshots=None if at_least is None else AtLeast(at_least=at_least)
            ),
        ),
        execution_policy=ExpireSnapshotsExecutionPolicy(older_than=timedelta(days=1), retain_last=retain_last),
    )


TWO_PARTITIONS = (part(6, value=1), part(2, value=2))


def _condition(key: str, observed: int, threshold: int) -> Measurement:
    return Measurement(
        key=key,
        observed=observed,
        unit=MeasurementUnit.COUNT,
        threshold=threshold,
        comparison=MeasurementComparison.AT_LEAST,
    )


def test_any_condition_holding_makes_operation_due():
    """Conditions combine with OR: one holding is enough, none holding or none at all is not."""
    holding = _condition("a", 5, 5)
    failing = _condition("b", 1, 5)
    context = Measurement(key="c", observed=1, unit=MeasurementUnit.BYTES)
    assert any_condition_holds((failing, holding, context))
    assert not any_condition_holds((failing, failing, context))
    assert not any_condition_holds(())
    assert not any_condition_holds((context,))


def test_due_when_reducible_files_reaches_threshold():
    """Compaction is due once the reducible files reach the condition's threshold."""
    a = assess(table(), obs(partitions=(part(5),)), Op.REWRITE_DATA_FILES, compaction(at_least=5))
    assert a.verdict == OperationVerdict.DUE


def test_not_due_when_reducible_files_below_threshold():
    """Compaction is not due while the reducible files stay below the condition's threshold."""
    a = assess(table(), obs(partitions=(part(4),)), Op.REWRITE_DATA_FILES, compaction(at_least=5))
    assert a.verdict == OperationVerdict.NOT_DUE
    assert a.planned is None


def test_empty_conditions_due_after_cooldown():
    """An operation without conditions is due as soon as its cooldown has passed."""
    t = table()
    assert assess(t, obs(), Op.REMOVE_ORPHAN_FILES).verdict == OperationVerdict.DUE
    t.operation_states[Op.REMOVE_ORPHAN_FILES] = OperationState(last_attempt_at=NOW - timedelta(days=6))
    assert assess(t, obs(), Op.REMOVE_ORPHAN_FILES).verdict == OperationVerdict.COOLDOWN
    t.operation_states[Op.REMOVE_ORPHAN_FILES] = OperationState(last_attempt_at=NOW - timedelta(days=7))
    assert assess(t, obs(), Op.REMOVE_ORPHAN_FILES).verdict == OperationVerdict.DUE


def test_compaction_without_condition_is_due_on_whole_table():
    """Compaction without a condition is due after its cooldown and compacts the whole table."""
    a = assess(table(), obs(partitions=TWO_PARTITIONS), Op.REWRITE_DATA_FILES, compaction(at_least=None))
    assert a.verdict == OperationVerdict.DUE
    assert a.planned is not None
    assert a.planned.partitions == ()
    assert a.threshold is None


def test_expire_snapshots_not_due_without_expirable_snapshot():
    """Snapshot expiry is not due when no snapshot is old enough and outside the retained ones."""
    a = assess(table(), obs(snapshots=snaps(10, 10)), Op.EXPIRE_SNAPSHOTS)
    assert (a.measured, a.verdict) == (0, OperationVerdict.NOT_DUE)


def test_expire_snapshots_threshold_comes_from_condition():
    """The expirable snapshots threshold is the condition's ``at_least``."""
    o = obs(snapshots=snaps(14, 14))
    a = assess(table(), o, Op.EXPIRE_SNAPSHOTS, snapshots(at_least=5))
    assert (a.measured, a.threshold, a.verdict) == (4, 5, OperationVerdict.NOT_DUE)


def test_reducible_files_measured_with_table_property_not_execution_value():
    """Compaction measures with the table's target size even when the execution policy sets its own."""
    policy = compaction(target_file_size_bytes=1024 * MIB)
    o = obs(properties={"write.target-file-size-bytes": str(128 * MIB)}, partitions=(part(6),))
    a = assess(table(), o, Op.REWRITE_DATA_FILES, policy)
    target = next(m for m in a.measurements if m.key == "target_file_size")
    assert target.observed == 134217728
    assert (a.size_bytes, a.size_source) == (134217728, SizeSource.TABLE_PROPERTY)


def test_partition_scope_counts_qualifying_partitions():
    """With partition scope, the measure counts the partitions that qualify for compaction."""
    a = assess(table(), obs(partitions=TWO_PARTITIONS), Op.REWRITE_DATA_FILES, compaction(at_least=5))
    assert a.verdict == OperationVerdict.DUE
    assert a.measured == 6
    assert a.qualifying_partitions == 1
    assert a.threshold == 5
    assert a.planned is not None
    assert a.planned.partitions == TWO_PARTITIONS[:1]


def test_table_scope_sums_every_partition():
    """With table scope, the measure sums the reducible files of every partition."""
    policy = compaction(unit=CompactionUnit.TABLE, at_least=5)
    a = assess(table(), obs(partitions=TWO_PARTITIONS), Op.REWRITE_DATA_FILES, policy)
    assert a.verdict == OperationVerdict.DUE
    assert a.measured == 8
    assert a.qualifying_partitions is None


@pytest.mark.parametrize(
    ("properties", "expected"),
    [
        ({"write.target-file-size-bytes": "2048"}, (2048, SizeSource.TABLE_PROPERTY)),
        ({}, (536870912, SizeSource.DEFAULT)),
    ],
)
def test_target_size_source(properties, expected):
    """The measured target file size comes from the table property or the default, and its source is reported."""
    a = assess(table(), obs(properties=properties), Op.REWRITE_DATA_FILES, compaction(target_file_size_bytes=1024))
    assert (a.size_bytes, a.size_source) == expected


def test_manifest_size_source():
    """The manifest size is taken from the condition, the table property or the default, and its source is reported."""
    o = obs(
        properties={"commit.manifest.target-size-bytes": str(MIB)},
        manifests=(ManifestStats(length_bytes=MIB // 2),) * 2,
    )
    a = assess(table(), o, Op.REWRITE_MANIFESTS)
    assert (a.size_bytes, a.size_source) == (MIB, SizeSource.TABLE_PROPERTY)
    assert (a.measured, a.threshold, a.verdict) == (2, 5, OperationVerdict.NOT_DUE)
    d = assess(table(), obs(), Op.REWRITE_MANIFESTS)
    assert (d.size_bytes, d.size_source) == (8 * MIB, SizeSource.DEFAULT)
    s = assess(table(), o, Op.REWRITE_MANIFESTS, manifests(smaller_than_bytes=MIB // 4))
    assert (s.size_bytes, s.size_source, s.measured) == (MIB // 4, SizeSource.CONDITION, 0)


def test_expire_snapshots_counts_expirable():
    """The snapshot expiry measure counts the snapshots that can be expired."""
    o = obs(snapshots=snaps(14, 14))
    a = assess(table(), o, Op.EXPIRE_SNAPSHOTS, snapshots(retain_last=10))
    assert (a.measured, a.threshold, a.verdict) == (4, 1, OperationVerdict.DUE)
    b = assess(table(), o, Op.EXPIRE_SNAPSHOTS, snapshots(retain_last=20))
    assert (b.measured, b.verdict) == (0, OperationVerdict.NOT_DUE)
    assert b.planned is None


def test_cooldown_reports_next_eligible_time():
    """An operation in cooldown reports when it is next eligible and has no plan."""
    t = table()
    t.operation_states[Op.REWRITE_DATA_FILES] = OperationState(last_attempt_at=NOW - timedelta(minutes=30))
    a = assess(t, obs(partitions=(part(10),)), Op.REWRITE_DATA_FILES)
    assert a.verdict == OperationVerdict.COOLDOWN
    assert a.next_eligible_at == NOW + timedelta(minutes=30)
    assert a.planned is None
    assert a.measured == 10


def test_cooldown_backs_off_after_failures():
    """Consecutive failures double the cooldown."""
    t = table()
    t.operation_states[Op.REWRITE_DATA_FILES] = OperationState(
        last_attempt_at=NOW - timedelta(hours=3), consecutive_failures=2
    )
    assert assess(t, obs(partitions=(part(10),)), Op.REWRITE_DATA_FILES).verdict == OperationVerdict.COOLDOWN
    t.operation_states[Op.REWRITE_DATA_FILES] = OperationState(
        last_attempt_at=NOW - timedelta(hours=4), consecutive_failures=2
    )
    assert assess(t, obs(partitions=(part(10),)), Op.REWRITE_DATA_FILES).verdict == OperationVerdict.DUE


def test_disabled_operation_has_no_measures():
    """A disabled operation reports no measure and no eligibility time."""
    policy = policy_with_operation(compaction(enabled=False), Op.REMOVE_ORPHAN_FILES, enabled=False)
    t = table()
    t.operation_states[Op.REMOVE_ORPHAN_FILES] = OperationState(last_attempt_at=NOW)
    a = assess(t, obs(), Op.REMOVE_ORPHAN_FILES, policy)
    assert a.verdict == OperationVerdict.DISABLED
    assert a.measured is None
    assert a.next_eligible_at is None
    c = assess(t, obs(partitions=(part(10),)), Op.REWRITE_DATA_FILES, policy)
    assert c.verdict == OperationVerdict.DISABLED
    assert (c.measured, c.threshold, c.size_bytes, c.size_source) == (None, None, None, None)


def test_assessment_ignores_status():
    """The assessment does not depend on the table status; the planner skips an unmanaged table before it."""
    t = table()
    t.unmanage(NOW)
    o = obs(partitions=(part(10),))
    assert assess(t, o, Op.REWRITE_DATA_FILES).verdict == OperationVerdict.DUE


def test_plan_equals_due_operations():
    """The plan of an assessment holds exactly its due operations, in order."""
    t = table()
    t.operation_states[Op.REWRITE_MANIFESTS] = OperationState(last_attempt_at=NOW - timedelta(minutes=10))
    o = obs(
        partitions=(part(10, value=1), part(1, value=2)),
        manifests=(ManifestStats(length_bytes=MIB),) * 5,
        snapshots=snaps(12, 11),
    )
    assessment = assess_maintenance(t, DEFAULT, o, NOW)
    assert [a.verdict for a in assessment.operations] == [
        OperationVerdict.DUE,
        OperationVerdict.COOLDOWN,
        OperationVerdict.DUE,
        OperationVerdict.DUE,
    ]
    assert [p.operation for p in assessment.plan().operations] == [
        Op.REWRITE_DATA_FILES,
        Op.EXPIRE_SNAPSHOTS,
        Op.REMOVE_ORPHAN_FILES,
    ]


def test_compaction_reports_reducible_files_and_context():
    """Partition-scope compaction reports reducible files, the target size and qualifying partitions."""
    a = assess(table(), obs(partitions=TWO_PARTITIONS), Op.REWRITE_DATA_FILES, compaction(at_least=5))
    assert a.measurements == (
        _condition("reducible_files", 6, 5),
        Measurement(key="target_file_size", observed=536870912, unit=MeasurementUnit.BYTES),
        Measurement(key="qualifying_partitions", observed=1, unit=MeasurementUnit.COUNT),
    )


def test_compaction_table_scope_has_no_qualifying_partitions_measurement():
    """Table-scope compaction reports no qualifying partitions."""
    policy = compaction(unit=CompactionUnit.TABLE, at_least=5)
    a = assess(table(), obs(partitions=TWO_PARTITIONS), Op.REWRITE_DATA_FILES, policy)
    assert a.measurements == (
        _condition("reducible_files", 8, 5),
        Measurement(key="target_file_size", observed=536870912, unit=MeasurementUnit.BYTES),
    )


def test_manifests_report_small_manifests():
    """Manifest rewriting reports the small manifests against the minimum."""
    o = obs(manifests=(ManifestStats(length_bytes=MIB),) * 4)
    a = assess(table(), o, Op.REWRITE_MANIFESTS, manifests(at_least=3))
    assert a.measurements == (_condition("small_manifests", 4, 3),)


def test_snapshots_report_expirable_snapshots():
    """Snapshot expiry reports the expirable snapshots against the condition's threshold."""
    a = assess(table(), obs(snapshots=snaps(14, 14)), Op.EXPIRE_SNAPSHOTS)
    assert a.measurements == (_condition("expirable_snapshots", 4, 1),)


def test_snapshots_without_condition_report_context_only():
    """Without a condition, snapshot expiry reports the expirable count as context and is due."""
    a = assess(table(), obs(snapshots=snaps(10, 10)), Op.EXPIRE_SNAPSHOTS, snapshots(at_least=None))
    assert a.measurements == (Measurement(key="expirable_snapshots", observed=0, unit=MeasurementUnit.COUNT),)
    assert a.verdict == OperationVerdict.DUE


def test_orphans_have_no_measurements():
    """Orphan file removal has no measurements."""
    assert assess(table(), obs(), Op.REMOVE_ORPHAN_FILES).measurements == ()


def test_disabled_operation_has_no_measurements():
    """A disabled operation has no measurements."""
    a = assess(table(), obs(partitions=(part(10),)), Op.REWRITE_DATA_FILES, compaction(enabled=False))
    assert a.measurements == ()


def test_cooldown_keeps_the_measurements():
    """An operation in cooldown keeps its measurements."""
    t = table()
    t.operation_states[Op.REWRITE_DATA_FILES] = OperationState(last_attempt_at=NOW - timedelta(minutes=30))
    a = assess(t, obs(partitions=(part(10),)), Op.REWRITE_DATA_FILES)
    assert a.verdict == OperationVerdict.COOLDOWN
    assert a.measurements[0] == _condition("reducible_files", 10, 5)


POLICY_V1 = AppliedPolicyRef(name="default", version=1, target=None)
OOM_AT_L = AttentionMark(since=NOW, reason="out of memory at size L", policy=POLICY_V1)


def _needing_attention(op: Op) -> Table:
    t = table()
    t.mark_needs_attention(op, OOM_AT_L, NOW - timedelta(days=2))
    return t


def test_needs_attention_blocks_only_its_operation_under_the_same_policy():
    """An operation marked under the applicable policy is not planned; the others still are."""
    t = _needing_attention(Op.REWRITE_DATA_FILES)
    o = obs(partitions=(part(10),), snapshots=snaps(12, 11))
    assessment = assess_maintenance(t, DEFAULT, o, NOW, applied=POLICY_V1)
    rdf = next(a for a in assessment.operations if a.operation == Op.REWRITE_DATA_FILES)
    assert rdf.verdict == OperationVerdict.NEEDS_ATTENTION
    assert rdf.planned is None
    assert rdf.measured == 10
    assert rdf.measurements
    expire = next(a for a in assessment.operations if a.operation == Op.EXPIRE_SNAPSHOTS)
    assert expire.verdict == OperationVerdict.DUE
    assert Op.REWRITE_DATA_FILES not in [p.operation for p in assessment.plan().operations]


def test_needs_attention_wins_over_cooldown():
    """An operation in cooldown that needs attention says it needs attention."""
    t = _needing_attention(Op.REWRITE_DATA_FILES)
    t.record_operation_result(Op.REWRITE_DATA_FILES, False, NOW - timedelta(minutes=1))
    a = next(
        a
        for a in assess_maintenance(t, DEFAULT, obs(partitions=(part(10),)), NOW, applied=POLICY_V1).operations
        if a.operation == Op.REWRITE_DATA_FILES
    )
    assert a.verdict == OperationVerdict.NEEDS_ATTENTION
    assert a.next_eligible_at is None


def test_a_changed_applicable_policy_lifts_needs_attention():
    """Under another version of the policy the operation is assessed as usual."""
    t = _needing_attention(Op.REWRITE_DATA_FILES)
    applied = AppliedPolicyRef(name="default", version=2, target=None)
    a = next(
        a
        for a in assess_maintenance(t, DEFAULT, obs(partitions=(part(10),)), NOW, applied=applied).operations
        if a.operation == Op.REWRITE_DATA_FILES
    )
    assert a.verdict == OperationVerdict.DUE


def test_without_an_applied_policy_the_mark_is_ignored():
    """An assessment that names no applicable policy ignores needs-attention marks."""
    t = _needing_attention(Op.REWRITE_DATA_FILES)
    assert assess(t, obs(partitions=(part(10),)), Op.REWRITE_DATA_FILES).verdict == OperationVerdict.DUE


def test_disabled_wins_over_needs_attention():
    """A disabled operation stays disabled even when it needs attention."""
    t = _needing_attention(Op.REWRITE_DATA_FILES)
    policy = compaction(enabled=False)
    a = next(
        a
        for a in assess_maintenance(t, policy, obs(partitions=(part(10),)), NOW, applied=POLICY_V1).operations
        if a.operation == Op.REWRITE_DATA_FILES
    )
    assert a.verdict == OperationVerdict.DISABLED
