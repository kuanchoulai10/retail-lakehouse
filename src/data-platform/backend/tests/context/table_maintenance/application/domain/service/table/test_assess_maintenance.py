"""Test the assessment of whether each maintenance operation is due for a table."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from context.table_maintenance.application.domain.model.shared import (
    ComputeSize,
    ManifestStats,
    Measurement,
    MeasurementComparison,
    MeasurementUnit,
    OperationAssessment,
    OperationVerdict,
    OverTargetPartition,
    PartitionFieldInfo,
    PartitionSpecInfo,
    PartitionStats,
    SizeSource,
    SnapshotInfo,
    TableId,
    TableObservation,
)
from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation as Op,
)
from context.table_maintenance.application.domain.model.table import (
    AppliedPolicyRef,
    AttentionMark,
    OperationCooldowns,
    OperationState,
    PartitionSelectionSettings,
    Table,
    TableName,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    DEFAULT_POLICY_ID,
    AtMost,
    CompactionUnit,
    ExpireSnapshotsSpec,
    ExpireSnapshotsTarget,
    MaintenancePolicyContent,
    RewriteDataFilesSpec,
    RewriteDataFilesTarget,
    RewriteManifestsSpec,
    RewriteManifestsTarget,
    TableMaintenancePolicyName,
)
from context.table_maintenance.application.domain.model.table_maintenance_run import ExpireSnapshotsJobContent
from context.table_maintenance.application.domain.service.table import (
    any_condition_holds,
    assess_maintenance,
)
from context.table_maintenance.application.domain.service.table_maintenance_run import build_maintenance_job_content
from tests.context.table_maintenance.discovery_decision_samples import MANAGED, UNMANAGED
from tests.context.table_maintenance.fakes.policy_with_operation import policy_with_operation

NOW = datetime(2026, 10, 24, 12, tzinfo=UTC)
MIB = 1024 * 1024
DEFAULT = MaintenancePolicyContent.platform_default()
PLATFORM = OperationCooldowns.platform_default()
DAY_SPEC = PartitionSpecInfo(
    spec_id=0,
    fields=(PartitionFieldInfo(field_id=1000, name="d", source_column="ts", source_type="timestamp", transform="day"),),
)


def table() -> Table:
    """Build a managed table."""
    return Table.register(
        TableId("u"),
        TableName(catalog="c", namespace="n", table="t"),
        MANAGED,
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


def assess(
    t: Table,
    o: TableObservation,
    op: Op,
    policy: MaintenancePolicyContent = DEFAULT,
    cooldowns: OperationCooldowns = PLATFORM,
) -> OperationAssessment:
    """Assess the table and return the assessment of one operation."""
    assessment = assess_maintenance(t, policy, o, NOW, cooldowns=cooldowns)
    assert [a.operation for a in assessment.operations] == list(Op.ordered())
    return next(a for a in assessment.operations if a.operation == op)


def compaction(*, at_most: int = 5, per: CompactionUnit = CompactionUnit.PARTITION) -> MaintenancePolicyContent:
    """Build a policy with the given compaction target."""
    return policy_with_operation(
        DEFAULT,
        Op.REWRITE_DATA_FILES,
        RewriteDataFilesSpec(target=RewriteDataFilesTarget(reducible_files=AtMost(at_most=at_most), per=per)),
    )


def manifests(*, at_most: int = 5) -> MaintenancePolicyContent:
    """Build a policy with the given small manifests target."""
    return policy_with_operation(
        DEFAULT,
        Op.REWRITE_MANIFESTS,
        RewriteManifestsSpec(target=RewriteManifestsTarget(small_manifests=AtMost(at_most=at_most))),
    )


def retention(
    *, min_snapshots_to_keep: int | None = 10, max_snapshot_age: timedelta | None = timedelta(days=1)
) -> MaintenancePolicyContent:
    """Build a policy with the given snapshot retention target."""
    return policy_with_operation(
        DEFAULT,
        Op.EXPIRE_SNAPSHOTS,
        ExpireSnapshotsSpec(
            target=ExpireSnapshotsTarget(min_snapshots_to_keep=min_snapshots_to_keep, max_snapshot_age=max_snapshot_age)
        ),
    )


def over(key: str, observed: int, at_most: int) -> Measurement:
    """Build the measurement of a count compared with its target."""
    return Measurement(
        key=key,
        observed=observed,
        unit=MeasurementUnit.COUNT,
        threshold=at_most,
        comparison=MeasurementComparison.MORE_THAN,
    )


TWO_PARTITIONS = (part(6, value=1), part(2, value=2))


def test_any_condition_holding_makes_operation_due():
    """One measurement over its target is enough; none over or none at all is not."""
    holding = over("a", 6, 5)
    failing = over("b", 5, 5)
    context = Measurement(key="c", observed=1, unit=MeasurementUnit.BYTES)
    assert any_condition_holds((failing, holding, context))
    assert not any_condition_holds((failing, failing, context))
    assert not any_condition_holds(())
    assert not any_condition_holds((context,))


@pytest.mark.parametrize("op", list(Op.ordered()))
def test_an_absent_block_is_disabled(op: Op):
    """An operation whose block the policy leaves out is not done: no measures, no eligibility time."""
    t = table()
    t.operation_states = {**t.operation_states, op: OperationState(last_attempt_at=NOW)}
    o = obs(partitions=(part(10),), manifests=(ManifestStats(length_bytes=MIB),) * 9, snapshots=snaps(14, 14))
    a = assess(t, o, op, policy_with_operation(DEFAULT, op, None))
    assert a.verdict == OperationVerdict.DISABLED
    assert a.measurements == ()
    assert (a.measured, a.threshold, a.size_bytes, a.size_source, a.next_eligible_at) == (None,) * 5
    assert a.planned is None


def test_reducible_files_at_the_target_is_not_due():
    """Per table, a total at the target is on target."""
    a = assess(table(), obs(partitions=(part(5),)), Op.REWRITE_DATA_FILES, compaction(per=CompactionUnit.TABLE))
    assert a.verdict == OperationVerdict.NOT_DUE
    assert a.measurements[0] == over("reducible_files", 5, 5)
    assert a.measurements[0].comparison == MeasurementComparison.MORE_THAN
    assert a.planned is None


def test_reducible_files_over_the_target_is_due():
    """Per table, a total over the target is due and compacts the whole table."""
    a = assess(table(), obs(partitions=(part(6),)), Op.REWRITE_DATA_FILES, compaction(per=CompactionUnit.TABLE))
    assert a.verdict == OperationVerdict.DUE
    assert (a.measured, a.threshold) == (6, 5)
    assert a.planned is not None
    assert a.planned.partitions == ()


def test_per_partition_compares_each_partition():
    """Per partition, two partitions of 3 stay on a target of 5 although they total 6."""
    a = assess(table(), obs(partitions=(part(3, value=1), part(3, value=2))), Op.REWRITE_DATA_FILES, compaction())
    assert a.verdict == OperationVerdict.NOT_DUE
    assert (a.measured, a.qualifying_partitions) == (0, 0)


def test_per_partition_counts_the_partitions_over_target():
    """Per partition, the reducible files are the sum over the partitions over the target."""
    o = obs(partitions=(part(7, value=1), part(1, value=2), part(9, value=3)))
    a = assess(table(), o, Op.REWRITE_DATA_FILES, compaction())
    assert a.verdict == OperationVerdict.DUE
    assert a.measurements == (
        over("reducible_files", 16, 5),
        Measurement(key="target_file_size", observed=536870912, unit=MeasurementUnit.BYTES),
        Measurement(key="qualifying_partitions", observed=2, unit=MeasurementUnit.COUNT),
        Measurement(key="selected_partitions", observed=2, unit=MeasurementUnit.COUNT),
        Measurement(key="waiting_partitions", observed=0, unit=MeasurementUnit.COUNT),
    )
    assert (a.measured, a.qualifying_partitions, a.threshold) == (16, 2, 5)
    assert a.planned is not None
    assert a.planned.partitions == (o.partitions[2], o.partitions[0])


def test_a_target_of_zero_makes_any_reducible_file_due():
    """``at_most: 0`` is due as soon as one file could be removed."""
    a = assess(table(), obs(partitions=(part(1),)), Op.REWRITE_DATA_FILES, compaction(at_most=0))
    assert a.verdict == OperationVerdict.DUE


def test_table_scope_has_no_qualifying_partitions_measurement():
    """Per table, the assessment reports the total and the target size only."""
    policy = compaction(per=CompactionUnit.TABLE)
    a = assess(table(), obs(partitions=TWO_PARTITIONS), Op.REWRITE_DATA_FILES, policy)
    assert a.measurements == (
        over("reducible_files", 8, 5),
        Measurement(key="target_file_size", observed=536870912, unit=MeasurementUnit.BYTES),
    )
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
    a = assess(table(), obs(properties=properties), Op.REWRITE_DATA_FILES)
    assert (a.size_bytes, a.size_source) == expected


def test_small_manifests_use_the_table_property():
    """A manifest is small under the table's manifest target size, else under 8 MiB."""
    o = obs(
        properties={"commit.manifest.target-size-bytes": "1024"},
        manifests=(ManifestStats(length_bytes=512),) * 6 + (ManifestStats(length_bytes=2048),),
    )
    a = assess(table(), o, Op.REWRITE_MANIFESTS)
    assert (a.size_bytes, a.size_source) == (1024, SizeSource.TABLE_PROPERTY)
    assert (a.measured, a.threshold, a.verdict) == (6, 5, OperationVerdict.DUE)
    assert a.measurements == (over("small_manifests", 6, 5),)
    d = assess(table(), obs(manifests=(ManifestStats(length_bytes=MIB),) * 5), Op.REWRITE_MANIFESTS)
    assert (d.size_bytes, d.size_source, d.measured, d.verdict) == (
        8 * MIB,
        SizeSource.DEFAULT,
        5,
        OperationVerdict.NOT_DUE,
    )


def test_small_manifests_follow_the_target():
    """The small manifests are compared with the policy's ``at_most``."""
    o = obs(manifests=(ManifestStats(length_bytes=MIB),) * 4)
    assert assess(table(), o, Op.REWRITE_MANIFESTS, manifests(at_most=3)).verdict == OperationVerdict.DUE
    assert assess(table(), o, Op.REWRITE_MANIFESTS, manifests(at_most=4)).verdict == OperationVerdict.NOT_DUE


def test_expirable_snapshots_over_zero_are_due():
    """Snapshot expiry is due once one snapshot falls outside the retention."""
    o = obs(snapshots=snaps(14, 14))
    a = assess(table(), o, Op.EXPIRE_SNAPSHOTS, retention(min_snapshots_to_keep=10))
    assert (a.measured, a.threshold, a.verdict) == (4, 0, OperationVerdict.DUE)
    assert a.measurements == (over("expirable_snapshots", 4, 0),)
    b = assess(table(), o, Op.EXPIRE_SNAPSHOTS, retention(min_snapshots_to_keep=20))
    assert (b.measured, b.verdict) == (0, OperationVerdict.NOT_DUE)
    assert b.planned is None


def test_expire_snapshots_not_due_without_expirable_snapshot():
    """Snapshot expiry is not due when no snapshot is old enough and outside the retained ones."""
    a = assess(table(), obs(snapshots=snaps(10, 10)), Op.EXPIRE_SNAPSHOTS)
    assert (a.measured, a.verdict) == (0, OperationVerdict.NOT_DUE)


def test_assessment_and_args_agree_on_retention():
    """A target silent on the count keeps the table's ``history.expire.min-snapshots-to-keep``, measured and run."""
    policy = retention(min_snapshots_to_keep=None, max_snapshot_age=timedelta(days=1))
    o = obs(properties={"history.expire.min-snapshots-to-keep": "3"}, snapshots=snaps(5, 5))
    a = assess(table(), o, Op.EXPIRE_SNAPSHOTS, policy)
    assert (a.measured, a.verdict) == (2, OperationVerdict.DUE)
    assert build_maintenance_job_content(Op.EXPIRE_SNAPSHOTS, policy, o.properties, NOW) == ExpireSnapshotsJobContent(
        older_than=NOW - timedelta(days=1), retain_last=3
    )


def test_a_never_by_age_property_still_assesses_and_runs():
    """Long.MAX in the table's age property, under a target silent on the age, is clamped to 100 years."""
    policy = retention(min_snapshots_to_keep=1, max_snapshot_age=None)
    o = obs(properties={"history.expire.max-snapshot-age-ms": "9223372036854775807"}, snapshots=snaps(5, 5))
    a = assess(table(), o, Op.EXPIRE_SNAPSHOTS, policy)
    assert (a.measured, a.verdict) == (0, OperationVerdict.NOT_DUE)
    assert build_maintenance_job_content(Op.EXPIRE_SNAPSHOTS, policy, o.properties, NOW) == ExpireSnapshotsJobContent(
        older_than=NOW - timedelta(days=36500), retain_last=1
    )


def test_retention_age_comes_from_the_target():
    """Snapshots younger than the target's age are kept."""
    policy = retention(min_snapshots_to_keep=1, max_snapshot_age=timedelta(days=3))
    a = assess(table(), obs(snapshots=snaps(5, 5)), Op.EXPIRE_SNAPSHOTS, policy)
    assert (a.measured, a.verdict) == (0, OperationVerdict.NOT_DUE)


def test_orphan_files_are_due_when_their_block_exists():
    """Orphan file removal has no target to measure: its block makes it due, the platform interval holds it back."""
    a = assess(table(), obs(), Op.REMOVE_ORPHAN_FILES)
    assert a.verdict == OperationVerdict.DUE
    assert a.measurements == ()
    assert a.threshold is None


def test_orphan_files_are_due_on_the_platform_interval():
    """Orphan file removal is due once the platform interval has passed since the last attempt."""
    t = table()
    weekly = PLATFORM.with_changes(remove_orphan_files=timedelta(days=7))
    t.operation_states = {
        **t.operation_states,
        Op.REMOVE_ORPHAN_FILES: OperationState(last_attempt_at=NOW - timedelta(days=8)),
    }
    assert assess(t, obs(), Op.REMOVE_ORPHAN_FILES, cooldowns=weekly).verdict == OperationVerdict.DUE
    t.operation_states = {
        **t.operation_states,
        Op.REMOVE_ORPHAN_FILES: OperationState(last_attempt_at=NOW - timedelta(days=6)),
    }
    assert assess(t, obs(), Op.REMOVE_ORPHAN_FILES, cooldowns=weekly).verdict == OperationVerdict.COOLDOWN
    daily = PLATFORM.with_changes(remove_orphan_files=timedelta(days=1))
    assert assess(t, obs(), Op.REMOVE_ORPHAN_FILES, cooldowns=daily).verdict == OperationVerdict.DUE


def test_cooldown_reports_next_eligible_time():
    """An operation in cooldown reports when it is next eligible, keeps its measures and has no plan."""
    t = table()
    t.operation_states = {
        **t.operation_states,
        Op.REWRITE_DATA_FILES: OperationState(last_attempt_at=NOW - timedelta(minutes=30)),
    }
    two_hours = PLATFORM.with_changes(rewrite_data_files=timedelta(hours=2))
    a = assess(t, obs(partitions=(part(10),)), Op.REWRITE_DATA_FILES, cooldowns=two_hours)
    assert a.verdict == OperationVerdict.COOLDOWN
    assert a.next_eligible_at == NOW + timedelta(minutes=90)
    assert a.planned is None
    assert a.measured == 10
    assert a.measurements[0] == over("reducible_files", 10, 5)


def test_the_platform_cooldown_holds_an_operation_back():
    """The cooldown of the platform settings holds an operation back; a zero one frees it."""
    t = table()
    t.operation_states = {
        **t.operation_states,
        Op.REWRITE_DATA_FILES: OperationState(last_attempt_at=NOW - timedelta(minutes=30)),
    }
    hour = PLATFORM.with_changes(rewrite_data_files=timedelta(hours=1))
    a = assess(t, obs(partitions=(part(10),)), Op.REWRITE_DATA_FILES, cooldowns=hour)
    assert a.verdict == OperationVerdict.COOLDOWN
    assert a.next_eligible_at == NOW + timedelta(minutes=30)
    free = PLATFORM.with_changes(rewrite_data_files=timedelta(0))
    assert assess(t, obs(partitions=(part(10),)), Op.REWRITE_DATA_FILES, cooldowns=free).verdict == OperationVerdict.DUE


def test_cooldown_backs_off_after_failures():
    """Consecutive failures double the platform cooldown."""
    t = table()
    hour = PLATFORM.with_changes(rewrite_data_files=timedelta(hours=1))
    t.operation_states = {
        **t.operation_states,
        Op.REWRITE_DATA_FILES: OperationState(last_attempt_at=NOW - timedelta(hours=3), consecutive_failures=2),
    }
    o = obs(partitions=(part(10),))
    assert assess(t, o, Op.REWRITE_DATA_FILES, cooldowns=hour).verdict == OperationVerdict.COOLDOWN
    t.operation_states = {
        **t.operation_states,
        Op.REWRITE_DATA_FILES: OperationState(last_attempt_at=NOW - timedelta(hours=4), consecutive_failures=2),
    }
    assert assess(t, o, Op.REWRITE_DATA_FILES, cooldowns=hour).verdict == OperationVerdict.DUE


def test_failures_double_the_platform_cooldown_up_to_the_cap():
    """Two failures make a 90-minute cooldown six hours; ten failures stop at the cap."""
    t = table()
    cooldowns = PLATFORM.with_changes(rewrite_data_files=timedelta(minutes=90), failure_backoff_cap=timedelta(hours=10))
    t.operation_states = {
        **t.operation_states,
        Op.REWRITE_DATA_FILES: OperationState(last_attempt_at=NOW - timedelta(hours=1), consecutive_failures=2),
    }
    two = assess(t, obs(partitions=(part(10),)), Op.REWRITE_DATA_FILES, cooldowns=cooldowns)
    assert two.next_eligible_at == NOW - timedelta(hours=1) + timedelta(hours=6)
    t.operation_states = {
        **t.operation_states,
        Op.REWRITE_DATA_FILES: OperationState(last_attempt_at=NOW - timedelta(hours=1), consecutive_failures=10),
    }
    ten = assess(t, obs(partitions=(part(10),)), Op.REWRITE_DATA_FILES, cooldowns=cooldowns)
    assert ten.next_eligible_at == NOW - timedelta(hours=1) + timedelta(hours=10)


def test_failure_backoff_stops_at_the_given_cap():
    """The doubling of the cooldown stops at the cap the caller passes, 24 hours by default."""
    t = table()
    t.operation_states = {
        **t.operation_states,
        Op.REWRITE_DATA_FILES: OperationState(last_attempt_at=NOW - timedelta(hours=1), consecutive_failures=10),
    }
    default = assess(t, obs(partitions=(part(10),)), Op.REWRITE_DATA_FILES)
    capped = assess(
        t,
        obs(partitions=(part(10),)),
        Op.REWRITE_DATA_FILES,
        cooldowns=PLATFORM.with_changes(failure_backoff_cap=timedelta(hours=3)),
    )
    assert default.next_eligible_at == NOW - timedelta(hours=1) + timedelta(hours=24)
    assert capped.next_eligible_at == NOW - timedelta(hours=1) + timedelta(hours=3)


def test_assessment_ignores_status():
    """The assessment does not depend on the table status; the planner skips an unmanaged table before it."""
    t = table()
    t.unmanage(UNMANAGED.match, NOW)
    o = obs(partitions=(part(10),))
    assert assess(t, o, Op.REWRITE_DATA_FILES).verdict == OperationVerdict.DUE


def test_plan_equals_due_operations():
    """The plan of an assessment holds exactly its due operations, in order."""
    t = table()
    t.operation_states = {
        **t.operation_states,
        Op.REWRITE_MANIFESTS: OperationState(last_attempt_at=NOW - timedelta(minutes=10)),
    }
    o = obs(
        partitions=(part(10, value=1), part(1, value=2)),
        manifests=(ManifestStats(length_bytes=MIB),) * 6,
        snapshots=snaps(12, 11),
    )
    assessment = assess_maintenance(t, DEFAULT, o, NOW, cooldowns=PLATFORM)
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


POLICY_V1 = AppliedPolicyRef(policy_id=DEFAULT_POLICY_ID, version=1, target=None)
OOM_AT_L = AttentionMark(
    since=NOW,
    reason="out of memory at size L",
    policy=POLICY_V1,
    policy_name=TableMaintenancePolicyName(value="default"),
)


def _needing_attention(op: Op) -> Table:
    t = table()
    t.mark_needs_attention(op, OOM_AT_L, NOW - timedelta(days=2))
    return t


def test_needs_attention_blocks_only_its_operation():
    """A marked operation is not planned, whatever policy applies (reconcile lifts stale marks); the others are."""
    t = _needing_attention(Op.REWRITE_DATA_FILES)
    o = obs(partitions=(part(10),), snapshots=snaps(12, 11))
    assessment = assess_maintenance(t, DEFAULT, o, NOW)
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
    a = assess(t, obs(partitions=(part(10),)), Op.REWRITE_DATA_FILES)
    assert a.verdict == OperationVerdict.NEEDS_ATTENTION
    assert a.next_eligible_at is None


def test_disabled_wins_over_needs_attention():
    """An operation the policy leaves out stays disabled even when it needs attention."""
    t = _needing_attention(Op.REWRITE_DATA_FILES)
    policy = policy_with_operation(DEFAULT, Op.REWRITE_DATA_FILES, None)
    a = assess(t, obs(partitions=(part(10),)), Op.REWRITE_DATA_FILES, policy)
    assert a.verdict == OperationVerdict.DISABLED


SELECTION = PartitionSelectionSettings.platform_default()


def written(partition: PartitionStats, at: datetime) -> PartitionStats:
    """Return the partition as last written at ``at``."""
    return partition.with_changes(last_written_at=at)


def _measurement(a, key):
    return next(m for m in a.measurements if m.key == key)


def _compaction_of(assessment):
    return next(o for o in assessment.operations if o.operation == Op.REWRITE_DATA_FILES)


def test_per_partition_plans_only_the_partitions_over_target():
    """Per partition, only the partitions over the target are planned, most reducible files first."""
    o = obs(partitions=(part(9, value=1), part(1, value=2), part(7, value=3)))
    a = _compaction_of(assess_maintenance(table(), compaction(), o, NOW))
    assert a.planned.partitions == (o.partitions[0], o.partitions[2])


def test_the_job_takes_at_most_the_cap():
    """A job takes at most the platform's partitions per job; the rest stay over the target."""
    o = obs(partitions=tuple(part(6 + i, value=i) for i in range(12)))
    a = _compaction_of(assess_maintenance(table(), compaction(), o, NOW, partition_selection=SELECTION))
    assert a.planned.partitions == tuple(sorted(o.partitions, key=lambda p: -p.data_file_count))[:10]
    assert len(a.planned.partitions) == 10
    assert _measurement(a, "selected_partitions").observed == 10
    assert _measurement(a, "qualifying_partitions").observed == 12
    assert _measurement(a, "waiting_partitions").observed == 0


def test_all_partitions_under_target_is_not_due():
    """With every partition under the target nothing is selected, waiting or tracked."""
    result = assess_maintenance(table(), compaction(), obs(partitions=(part(3),)), NOW)
    a = _compaction_of(result)
    assert a.verdict == OperationVerdict.NOT_DUE
    assert (_measurement(a, "selected_partitions").observed, _measurement(a, "waiting_partitions").observed) == (0, 0)
    assert result.over_target_partitions == ()


def test_every_partition_being_written_waits():
    """When every partition over the target is being written the compaction waits for writes."""
    o = obs(partitions=tuple(written(part(9, value=v), NOW - timedelta(seconds=30)) for v in (1, 2)))
    a = _compaction_of(assess_maintenance(table(), compaction(), o, NOW))
    assert (a.verdict, a.planned, a.next_eligible_at) == (
        OperationVerdict.WAITING_FOR_WRITES,
        None,
        NOW + timedelta(seconds=90),
    )
    assert _measurement(a, "waiting_partitions").observed == 2


def test_some_waiting_some_selected_is_due():
    """A partition that waits does not hold back one that may run."""
    o = obs(partitions=(written(part(9, value=1), NOW - timedelta(seconds=30)), part(9, value=2)))
    a = _compaction_of(assess_maintenance(table(), compaction(), o, NOW))
    assert a.verdict == OperationVerdict.DUE
    assert (_measurement(a, "selected_partitions").observed, _measurement(a, "waiting_partitions").observed) == (1, 1)


def test_a_partition_over_target_for_an_hour_runs_while_written():
    """A partition over the target for the longest wait runs although it is still being written."""
    hot = written(part(9, value=1), NOW - timedelta(seconds=10))
    t = table()
    t.record_over_target_partitions((OverTargetPartition(spec_id=0, values=(1,), since=NOW - timedelta(minutes=61)),))
    a = _compaction_of(assess_maintenance(t, compaction(), obs(partitions=(hot,)), NOW))
    assert a.planned.partitions == (hot,)


def test_waiting_and_cooldown_reads_cooldown():
    """A compaction that waits and is in cooldown says it is cooling down."""
    t = table()
    t.record_operation_result(Op.REWRITE_DATA_FILES, True, NOW - timedelta(minutes=10), size=ComputeSize.S)
    o = obs(partitions=(written(part(9), NOW - timedelta(seconds=30)),))
    a = _compaction_of(assess_maintenance(t, compaction(), o, NOW))
    assert (a.verdict, a.next_eligible_at) == (
        OperationVerdict.COOLDOWN,
        NOW - timedelta(minutes=10) + PLATFORM.rewrite_data_files,
    )


def test_waiting_and_needs_attention_reads_needs_attention():
    """A compaction that waits and needs attention says so, and the over-target partitions are still tracked."""
    t = _needing_attention(Op.REWRITE_DATA_FILES)
    result = assess_maintenance(t, compaction(), obs(partitions=(written(part(9), NOW),)), NOW)
    a = _compaction_of(result)
    assert (a.verdict, a.planned, a.next_eligible_at) == (OperationVerdict.NEEDS_ATTENTION, None, None)
    assert len(result.over_target_partitions) == 1


def test_the_assessment_returns_the_tracked_partitions():
    """The assessment keeps the since of a tracked partition and starts a new one at now."""
    t = table()
    t.record_over_target_partitions((OverTargetPartition(spec_id=0, values=(3,), since=NOW - timedelta(hours=2)),))
    o = obs(partitions=(part(9, value=1), part(1, value=2), part(9, value=3)))
    assert assess_maintenance(t, compaction(), o, NOW).over_target_partitions == (
        OverTargetPartition(spec_id=0, values=(1,), since=NOW),
        OverTargetPartition(spec_id=0, values=(3,), since=NOW - timedelta(hours=2)),
    )


def test_tracking_continues_during_cooldown():
    """A cooldown does not hide the over-target partitions, so their since is not restarted."""
    t = table()
    t.record_operation_result(Op.REWRITE_DATA_FILES, True, NOW - timedelta(minutes=10), size=ComputeSize.S)
    result = assess_maintenance(t, compaction(), obs(partitions=(part(9),)), NOW)
    assert _compaction_of(result).verdict == OperationVerdict.COOLDOWN
    assert len(result.over_target_partitions) == 1


def test_per_table_ignores_quiet_and_the_cap():
    """Per table, the whole table is compacted with no cap, no quiet period and no tracking."""
    o = obs(partitions=tuple(written(part(9, value=i), NOW) for i in range(12)))
    result = assess_maintenance(table(), compaction(per=CompactionUnit.TABLE), o, NOW)
    a = _compaction_of(result)
    assert (a.verdict, a.planned.partitions, result.over_target_partitions) == (OperationVerdict.DUE, (), ())


def test_no_compaction_block_tracks_nothing():
    """A policy without a compaction block tracks no partition."""
    policy = DEFAULT.with_changes(rewrite_data_files=None)
    assert assess_maintenance(table(), policy, obs(partitions=(part(9),)), NOW).over_target_partitions == ()


def test_partitions_of_an_older_spec_are_selected():
    """Partitions of an older spec are compared and selected with the current ones."""
    month = PartitionSpecInfo(
        spec_id=1,
        fields=(
            PartitionFieldInfo(field_id=1001, name="m", source_column="ts", source_type="timestamp", transform="month"),
        ),
    )
    o = obs(specs=(DAY_SPEC, month), partitions=(part(9, value=1), part(8, spec_id=1, value=2)))
    a = _compaction_of(assess_maintenance(table(), compaction(), o, NOW))
    assert {p.spec_id for p in a.planned.partitions} == {0, 1}


def test_a_selected_unpartitioned_partition_plans_the_whole_table():
    """A selected partition of an unpartitioned spec plans the whole table."""
    flat = PartitionSpecInfo(spec_id=1, fields=())
    unpartitioned = PartitionStats(
        spec_id=1,
        values=(),
        data_file_count=9,
        position_delete_file_count=0,
        equality_delete_file_count=0,
        total_data_file_size_bytes=0,
    )
    o = obs(specs=(DAY_SPEC, flat), partitions=(part(9, value=1), unpartitioned))
    a = _compaction_of(assess_maintenance(table(), compaction(), o, NOW))
    assert (a.verdict, a.planned.partitions) == (OperationVerdict.DUE, ())


def _flat(reducible: int, spec_id: int = 1) -> PartitionStats:
    return PartitionStats(
        spec_id=spec_id,
        values=(),
        data_file_count=reducible,
        position_delete_file_count=0,
        equality_delete_file_count=0,
        total_data_file_size_bytes=0,
    )


def test_an_unpartitioned_partition_under_the_target_does_not_widen_the_plan():
    """The whole-table rule looks at the selection only: a flat partition under the target is not in it."""
    flat = PartitionSpecInfo(spec_id=1, fields=())
    o = obs(specs=(DAY_SPEC, flat), partitions=(part(9, value=1), _flat(2)))
    a = _compaction_of(assess_maintenance(table(), compaction(), o, NOW))
    assert a.planned.partitions == (o.partitions[0],)


def test_an_unpartitioned_partition_that_waits_does_not_widen_the_plan():
    """A flat partition over the target that waits for writes is not selected, so the plan stays partitioned."""
    flat = PartitionSpecInfo(spec_id=1, fields=())
    o = obs(specs=(DAY_SPEC, flat), partitions=(part(9, value=1), written(_flat(9), NOW)))
    a = _compaction_of(assess_maintenance(table(), compaction(), o, NOW))
    assert a.planned.partitions == (o.partitions[0],)
    assert _measurement(a, "waiting_partitions").observed == 1


def test_a_partition_of_an_unknown_spec_under_the_target_does_not_widen_the_plan():
    """A partition whose spec the observation does not list, under the target, is not in the selection."""
    o = obs(partitions=(part(9, value=1), _flat(2, spec_id=7)))
    a = _compaction_of(assess_maintenance(table(), compaction(), o, NOW))
    assert a.planned.partitions == (o.partitions[0],)


def test_a_selected_partition_of_an_unknown_spec_plans_the_whole_table():
    """A selected partition whose spec the observation does not list plans the whole table."""
    o = obs(partitions=(part(9, value=1), _flat(9, spec_id=7)))
    a = _compaction_of(assess_maintenance(table(), compaction(), o, NOW))
    assert (a.verdict, a.planned.partitions) == (OperationVerdict.DUE, ())


def test_a_non_finite_partition_over_target_is_due_but_not_tracked():
    """A partition with a NaN value is still compacted when over the target, but left out of the record."""
    nan = part(9, value=float("nan"))
    result = assess_maintenance(table(), compaction(), obs(partitions=(nan,)), NOW)
    a = _compaction_of(result)
    assert (a.verdict, a.planned.partitions, result.over_target_partitions) == (OperationVerdict.DUE, (nan,), ())
