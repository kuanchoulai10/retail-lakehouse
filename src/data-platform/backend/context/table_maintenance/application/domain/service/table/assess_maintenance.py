"""Define the assess_maintenance domain service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceAssessment,
    MaintenanceOperation,
    Measurement,
    MeasurementComparison,
    MeasurementUnit,
    OperationAssessment,
    OperationVerdict,
    OverTargetPartition,
    PlannedOperation,
    SizeSource,
    TableObservation,
)
from context.table_maintenance.application.domain.model.table import (
    DEFAULT_OPERATION_COOLDOWNS,
    DEFAULT_PARTITION_SELECTION_SETTINGS,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    CompactionUnit,
    ExpireSnapshotsSpec,
    MaintenancePolicyContent,
    RewriteDataFilesSpec,
    RewriteManifestsSpec,
)
from context.table_maintenance.application.domain.service.shared import (
    TARGET_FILE_SIZE_PROPERTY,
    positive_int_property,
    resolve_snapshot_retention,
    resolve_target_file_size,
)
from context.table_maintenance.application.domain.service.table.any_condition_holds import (
    any_condition_holds,
)
from context.table_maintenance.application.domain.service.table.compute_reducible_files import (
    compute_reducible_files,
)
from context.table_maintenance.application.domain.service.table.select_compaction_partitions import (
    select_compaction_partitions,
)
from context.table_maintenance.application.domain.service.table.track_over_target_partitions import (
    track_over_target_partitions,
)

if TYPE_CHECKING:
    from datetime import datetime

    from context.table_maintenance.application.domain.model.table import (
        OperationCooldowns,
        PartitionSelectionSettings,
        Table,
    )

DEFAULT_SMALL_MANIFEST_BYTES = 8 * 1024 * 1024
MANIFEST_TARGET_SIZE_PROPERTY = "commit.manifest.target-size-bytes"


def assess_maintenance(
    table: Table,
    policy: MaintenancePolicyContent,
    observation: TableObservation,
    now: datetime,
    *,
    cooldowns: OperationCooldowns = DEFAULT_OPERATION_COOLDOWNS,
    partition_selection: PartitionSelectionSettings = DEFAULT_PARTITION_SELECTION_SETTINGS,
) -> MaintenanceAssessment:
    """Evaluate every operation of a table against a policy's target state, regardless of the table's status.

    An operation whose block the policy leaves out is disabled. Compaction, manifest rewriting and
    snapshot expiry are due when the table is off their target: more reducible files or small
    manifests than ``at_most``, or any snapshot outside the retention. Orphan file removal has no
    target the platform can measure, so its block alone makes it due and the platform interval holds
    it back. An operation marked as needing attention is never due, whatever its cooldown; a mark set
    under an earlier applicable policy is lifted by the plan, not ignored here. The cooldown is the
    platform's (``cooldowns``); the failure backoff doubles it per consecutive failure up to
    ``cooldowns.failure_backoff_cap``.

    A compaction per partition takes only the partitions over the target that
    ``partition_selection`` allows: those over the target for the longest wait first (oldest first), then
    the most reducible files first, at most ``partitions_per_job``,
    leaving out those still being written (see ``select_compaction_partitions``). When every
    partition over the target is still being written, the compaction is ``WAITING_FOR_WRITES``.
    The assessment also returns the partitions over the target with since when, whatever
    the compaction's verdict, so the plan can record them.
    """
    assessed = [
        _assess(op, table, policy, observation, now, cooldowns, partition_selection)
        for op in MaintenanceOperation.ordered()
    ]
    return MaintenanceAssessment(
        operations=tuple(assessment for assessment, _ in assessed),
        # Only the compaction tracks partitions, so at most one operation returns a non-empty tuple.
        over_target_partitions=next((tracked for _, tracked in assessed if tracked), ()),
    )


def _assess(
    op: MaintenanceOperation,
    table: Table,
    policy: MaintenancePolicyContent,
    observation: TableObservation,
    now: datetime,
    cooldowns: OperationCooldowns,
    partition_selection: PartitionSelectionSettings,
) -> tuple[OperationAssessment, tuple[OverTargetPartition, ...]]:
    """Return the assessment of one operation and the over-target partitions it tracked.

    The tracked partitions leave ``_measure`` beside the assessment, so the needs-attention and
    cooldown overrides below cannot drop them.
    """
    if policy.spec_for(op) is None:
        return OperationAssessment(operation=op, verdict=OperationVerdict.DISABLED), ()
    measured, planned, tracked = _measure(op, table, policy, observation, now, partition_selection)
    waiting = measured.verdict == OperationVerdict.WAITING_FOR_WRITES
    if op == MaintenanceOperation.REMOVE_ORPHAN_FILES or (not waiting and any_condition_holds(measured.measurements)):
        assessment = measured.with_changes(
            verdict=OperationVerdict.DUE,
            planned=PlannedOperation(operation=op) if planned is None else planned,
        )
    else:
        assessment = measured
    state = table.operation_state(op)
    if state.attention is not None:
        return (
            assessment.with_changes(verdict=OperationVerdict.NEEDS_ATTENTION, next_eligible_at=None, planned=None),
            tracked,
        )
    if state.last_attempt_at is None:
        return assessment, tracked
    next_eligible_at = state.last_attempt_at + state.effective_cooldown(
        cooldowns.for_operation(op), cooldowns.failure_backoff_cap
    )
    if now >= next_eligible_at:
        return assessment, tracked
    return (
        assessment.with_changes(
            verdict=OperationVerdict.COOLDOWN,
            next_eligible_at=next_eligible_at,
            planned=None,
        ),
        tracked,
    )


def _measure(
    op: MaintenanceOperation,
    table: Table,
    policy: MaintenancePolicyContent,
    observation: TableObservation,
    now: datetime,
    partition_selection: PartitionSelectionSettings,
) -> tuple[OperationAssessment, PlannedOperation | None, tuple[OverTargetPartition, ...]]:
    """Return the not-due assessment with its measurements, the operation to plan if due, and the tracked partitions.

    A planned operation of None means the whole table. Only a compaction per partition tracks partitions.
    """
    match op:
        case MaintenanceOperation.REWRITE_DATA_FILES if policy.rewrite_data_files is not None:
            return _measure_compaction(policy.rewrite_data_files, observation, table, now, partition_selection)
        case MaintenanceOperation.REWRITE_MANIFESTS if policy.rewrite_manifests is not None:
            return _measure_manifests(policy.rewrite_manifests, observation), None, ()
        case MaintenanceOperation.EXPIRE_SNAPSHOTS if policy.expire_snapshots is not None:
            return _measure_snapshots(policy.expire_snapshots, observation, now), None, ()
        case MaintenanceOperation.REMOVE_ORPHAN_FILES:
            # No target the platform can measure: nothing to compare, the block alone makes it due.
            return OperationAssessment(operation=op, verdict=OperationVerdict.NOT_DUE), None, ()
        case _:
            # The policy leaves the operation out: nothing to measure. ``_assess`` reports it
            # disabled before measuring, so this keeps the same verdict.
            return OperationAssessment(operation=op, verdict=OperationVerdict.DISABLED), None, ()


def _over(key: str, observed: int, at_most: int) -> Measurement:
    """Return a count compared with its target: met (due) when it is over ``at_most``."""
    return Measurement(
        key=key,
        observed=observed,
        unit=MeasurementUnit.COUNT,
        threshold=at_most,
        comparison=MeasurementComparison.MORE_THAN,
    )


def _measure_compaction(
    spec: RewriteDataFilesSpec,
    observation: TableObservation,
    table: Table,
    now: datetime,
    partition_selection: PartitionSelectionSettings,
) -> tuple[OperationAssessment, PlannedOperation | None, tuple[OverTargetPartition, ...]]:
    """Measure the reducible files against the target, per partition or across the table.

    Per partition, each partition is compared on its own; the reducible files are the sum over the
    partitions over the target, which are the qualifying partitions. The job takes the selection
    of those partitions; if all of them wait for writes to settle, the verdict is
    ``WAITING_FOR_WRITES`` until the earliest of them may run.
    """
    op = MaintenanceOperation.REWRITE_DATA_FILES
    at_most = spec.target.reducible_files.at_most
    target = resolve_target_file_size(observation.properties)
    source = (
        SizeSource.TABLE_PROPERTY
        if positive_int_property(observation.properties, TARGET_FILE_SIZE_PROPERTY)
        else SizeSource.DEFAULT
    )
    reducible = [(p, compute_reducible_files(p, target)) for p in observation.partitions]
    base = OperationAssessment(
        operation=op,
        verdict=OperationVerdict.NOT_DUE,
        threshold=at_most,
        size_bytes=target,
        size_source=source,
    )
    target_size = Measurement(key="target_file_size", observed=target, unit=MeasurementUnit.BYTES)
    if spec.target.per == CompactionUnit.TABLE:
        total = sum(r for _, r in reducible)
        measured = base.with_changes(
            measured=total, measurements=(_over("reducible_files", total, at_most), target_size)
        )
        return measured, None, ()
    qualifying = [(p, r) for p, r in reducible if r > at_most]
    total = sum(r for _, r in qualifying)
    tracked = track_over_target_partitions(table.over_target_partitions, [p for p, _ in qualifying], now)
    selection = select_compaction_partitions(qualifying, tracked, now, partition_selection)
    measured = base.with_changes(
        measured=total,
        qualifying_partitions=len(qualifying),
        measurements=(
            _over("reducible_files", total, at_most),
            target_size,
            Measurement(key="qualifying_partitions", observed=len(qualifying), unit=MeasurementUnit.COUNT),
            Measurement(key="selected_partitions", observed=len(selection.selected), unit=MeasurementUnit.COUNT),
            Measurement(key="waiting_partitions", observed=len(selection.waiting), unit=MeasurementUnit.COUNT),
        ),
    )
    if selection.all_waiting:
        waiting = measured.with_changes(
            verdict=OperationVerdict.WAITING_FOR_WRITES, next_eligible_at=selection.waiting_until
        )
        return waiting, None, tracked
    partitioned = {s.spec_id for s in observation.specs if not s.is_unpartitioned}
    if not selection.selected or any(p.spec_id not in partitioned for p in selection.selected):
        return measured, None, tracked
    return measured, PlannedOperation(operation=op, partitions=selection.selected), tracked


def _measure_manifests(spec: RewriteManifestsSpec, observation: TableObservation) -> OperationAssessment:
    """Count the manifests under the table's manifest target size, else under 8 MiB, against the target."""
    at_most = spec.target.small_manifests.at_most
    prop = positive_int_property(observation.properties, MANIFEST_TARGET_SIZE_PROPERTY)
    if prop is not None:
        threshold, source = prop, SizeSource.TABLE_PROPERTY
    else:
        threshold, source = DEFAULT_SMALL_MANIFEST_BYTES, SizeSource.DEFAULT
    small = sum(1 for m in observation.manifests if m.length_bytes < threshold)
    return OperationAssessment(
        operation=MaintenanceOperation.REWRITE_MANIFESTS,
        verdict=OperationVerdict.NOT_DUE,
        measured=small,
        threshold=at_most,
        size_bytes=threshold,
        size_source=source,
        measurements=(_over("small_manifests", small, at_most),),
    )


def _measure_snapshots(spec: ExpireSnapshotsSpec, observation: TableObservation, now: datetime) -> OperationAssessment:
    """Count the snapshots outside the resolved retention, the same retention the procedure is run with."""
    retention = resolve_snapshot_retention(spec.target, observation.properties)
    newest_first = sorted(observation.snapshots, key=lambda s: s.committed_at, reverse=True)
    cutoff = now - retention.max_snapshot_age
    expirable = sum(
        1
        for s in newest_first[retention.min_snapshots_to_keep :]
        if s.committed_at < cutoff and s.snapshot_id != observation.current_snapshot_id
    )
    return OperationAssessment(
        operation=MaintenanceOperation.EXPIRE_SNAPSHOTS,
        verdict=OperationVerdict.NOT_DUE,
        measured=expirable,
        threshold=0,
        measurements=(_over("expirable_snapshots", expirable, 0),),
    )
