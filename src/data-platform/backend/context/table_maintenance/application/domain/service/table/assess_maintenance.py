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
    PlannedOperation,
    SizeSource,
    TableObservation,
)
from context.table_maintenance.application.domain.model.table import DEFAULT_OPERATION_COOLDOWNS
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    AtLeast,
    CompactionUnit,
    ExpireSnapshotsPolicy,
    MaintenancePolicyContent,
    RewriteDataFilesPolicy,
    RewriteManifestsPolicy,
    SmallManifestsCondition,
)
from context.table_maintenance.application.domain.service.shared import (
    TARGET_FILE_SIZE_PROPERTY,
    positive_int_property,
    resolve_target_file_size,
)
from context.table_maintenance.application.domain.service.table.any_condition_holds import (
    any_condition_holds,
)
from context.table_maintenance.application.domain.service.table.compute_reducible_files import (
    compute_reducible_files,
)

if TYPE_CHECKING:
    from datetime import datetime

    from context.table_maintenance.application.domain.model.table import OperationCooldowns, Table

DEFAULT_SMALL_MANIFEST_BYTES = 8 * 1024 * 1024
MANIFEST_TARGET_SIZE_PROPERTY = "commit.manifest.target-size-bytes"


def assess_maintenance(
    table: Table,
    policy: MaintenancePolicyContent,
    observation: TableObservation,
    now: datetime,
    *,
    cooldowns: OperationCooldowns = DEFAULT_OPERATION_COOLDOWNS,
) -> MaintenanceAssessment:
    """Evaluate every operation of a table against a policy, regardless of the table's status.

    An operation is due when it is enabled, its cooldown (with the failure backoff)
    has passed, and its conditions are empty or any of them holds. An enabled operation
    marked as needing attention is never due, whatever its cooldown; a mark set under an
    earlier applicable policy is lifted by the plan, not ignored here. The cooldown is the
    platform's (``cooldowns``), not the policy's; the failure backoff doubles it per
    consecutive failure up to ``cooldowns.failure_backoff_cap``.
    """
    return MaintenanceAssessment(
        operations=tuple(
            _assess(op, table, policy, observation, now, cooldowns) for op in MaintenanceOperation.ordered()
        )
    )


def _assess(
    op: MaintenanceOperation,
    table: Table,
    policy: MaintenancePolicyContent,
    observation: TableObservation,
    now: datetime,
    cooldowns: OperationCooldowns,
) -> OperationAssessment:
    operation_policy = policy.operations.for_operation(op)
    if not operation_policy.enabled:
        return OperationAssessment(operation=op, verdict=OperationVerdict.DISABLED)
    measured, planned = _measure(op, policy, observation, now)
    conditions = operation_policy.trigger_policy.conditions
    if conditions.is_empty() or any_condition_holds(measured.measurements):
        assessment = measured.with_changes(
            verdict=OperationVerdict.DUE,
            planned=PlannedOperation(operation=op) if planned is None else planned,
        )
    else:
        assessment = measured
    state = table.operation_state(op)
    if state.attention is not None:
        return assessment.with_changes(verdict=OperationVerdict.NEEDS_ATTENTION, planned=None)
    if state.last_attempt_at is None:
        return assessment
    next_eligible_at = state.last_attempt_at + state.effective_cooldown(
        cooldowns.for_operation(op), cooldowns.failure_backoff_cap
    )
    if now >= next_eligible_at:
        return assessment
    return assessment.with_changes(
        verdict=OperationVerdict.COOLDOWN,
        next_eligible_at=next_eligible_at,
        planned=None,
    )


def _measure(
    op: MaintenanceOperation,
    policy: MaintenancePolicyContent,
    observation: TableObservation,
    now: datetime,
) -> tuple[OperationAssessment, PlannedOperation | None]:
    """Return the not-due assessment with its measurements, and the operation to plan if it is due.

    A planned operation of None means the whole table.
    """
    match op:
        case MaintenanceOperation.REWRITE_DATA_FILES:
            return _measure_compaction(policy.operations.rewrite_data_files, observation)
        case MaintenanceOperation.REWRITE_MANIFESTS:
            return _measure_manifests(policy.operations.rewrite_manifests, observation), None
        case MaintenanceOperation.EXPIRE_SNAPSHOTS:
            return _measure_snapshots(policy.operations.expire_snapshots, observation, now), None
        case MaintenanceOperation.REMOVE_ORPHAN_FILES:
            return OperationAssessment(operation=op, verdict=OperationVerdict.NOT_DUE), None


def _at_least(condition: AtLeast | SmallManifestsCondition | None) -> int | None:
    return None if condition is None else condition.at_least


def _count(key: str, observed: int, at_least: int | None) -> Measurement:
    """Return a count, compared with the condition's threshold when there is one."""
    if at_least is None:
        return Measurement(key=key, observed=observed, unit=MeasurementUnit.COUNT)
    return Measurement(
        key=key,
        observed=observed,
        unit=MeasurementUnit.COUNT,
        threshold=at_least,
        comparison=MeasurementComparison.AT_LEAST,
    )


def _measure_compaction(
    policy: RewriteDataFilesPolicy, observation: TableObservation
) -> tuple[OperationAssessment, PlannedOperation | None]:
    op = MaintenanceOperation.REWRITE_DATA_FILES
    condition = policy.trigger_policy.conditions.reducible_files
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
        threshold=_at_least(condition),
        size_bytes=target,
        size_source=source,
    )
    target_size = Measurement(key="target_file_size", observed=target, unit=MeasurementUnit.BYTES)
    if policy.scope.unit == CompactionUnit.TABLE or condition is None:
        total = sum(r for _, r in reducible)
        measured = base.with_changes(
            measured=total, measurements=(_count("reducible_files", total, _at_least(condition)), target_size)
        )
        return measured, None
    qualifying = [(p, r) for p, r in reducible if r >= condition.at_least]
    total = sum(r for _, r in qualifying)
    measured = base.with_changes(
        measured=total,
        qualifying_partitions=len(qualifying),
        measurements=(
            _count("reducible_files", total, _at_least(condition)),
            target_size,
            Measurement(key="qualifying_partitions", observed=len(qualifying), unit=MeasurementUnit.COUNT),
        ),
    )
    selected = tuple(p for p, _ in qualifying)
    partitioned = {s.spec_id for s in observation.specs if not s.is_unpartitioned}
    if not selected or any(p.spec_id not in partitioned for p in selected):
        return measured, None
    return measured, PlannedOperation(operation=op, partitions=selected)


def _measure_manifests(policy: RewriteManifestsPolicy, observation: TableObservation) -> OperationAssessment:
    condition = policy.trigger_policy.conditions.small_manifests
    prop = positive_int_property(observation.properties, MANIFEST_TARGET_SIZE_PROPERTY)
    if condition is not None and condition.smaller_than_bytes is not None:
        threshold, source = condition.smaller_than_bytes, SizeSource.CONDITION
    elif prop is not None:
        threshold, source = prop, SizeSource.TABLE_PROPERTY
    else:
        threshold, source = DEFAULT_SMALL_MANIFEST_BYTES, SizeSource.DEFAULT
    small = sum(1 for m in observation.manifests if m.length_bytes < threshold)
    return OperationAssessment(
        operation=MaintenanceOperation.REWRITE_MANIFESTS,
        verdict=OperationVerdict.NOT_DUE,
        measured=small,
        threshold=_at_least(condition),
        size_bytes=threshold,
        size_source=source,
        measurements=(_count("small_manifests", small, _at_least(condition)),),
    )


def _measure_snapshots(
    policy: ExpireSnapshotsPolicy, observation: TableObservation, now: datetime
) -> OperationAssessment:
    """Count the snapshots the execution policy would expire: the one condition that reads execution values."""
    execution = policy.execution_policy
    condition = policy.trigger_policy.conditions.expirable_snapshots
    newest_first = sorted(observation.snapshots, key=lambda s: s.committed_at, reverse=True)
    cutoff = now - execution.older_than
    expirable = sum(
        1
        for s in newest_first[execution.retain_last :]
        if s.committed_at < cutoff and s.snapshot_id != observation.current_snapshot_id
    )
    return OperationAssessment(
        operation=MaintenanceOperation.EXPIRE_SNAPSHOTS,
        verdict=OperationVerdict.NOT_DUE,
        measured=expirable,
        threshold=_at_least(condition),
        measurements=(_count("expirable_snapshots", expirable, _at_least(condition)),),
    )
