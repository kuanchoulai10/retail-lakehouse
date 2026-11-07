"""Define the assess_maintenance domain service."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from application.domain.model.shared import (
    CompactionScope,
    MaintenanceAssessment,
    MaintenanceOperation,
    MaintenanceSettings,
    OperationAssessment,
    OperationVerdict,
    PlannedOperation,
    SizeSource,
    TableObservation,
)
from application.domain.model.table import Table
from application.domain.service.table.compute_reducible_files import (
    compute_reducible_files,
)
from application.domain.service.shared import (
    positive_int_property,
    resolve_target_file_size,
)

DEFAULT_SMALL_MANIFEST_BYTES = 8 * 1024 * 1024
MANIFEST_TARGET_SIZE_PROPERTY = "commit.manifest.target-size-bytes"
TARGET_FILE_SIZE_PROPERTY = "write.target-file-size-bytes"


def assess_maintenance(
    table: Table,
    settings: MaintenanceSettings,
    observation: TableObservation,
    now: datetime,
) -> MaintenanceAssessment:
    """Evaluate every operation of a table, regardless of the table's status."""
    return MaintenanceAssessment(
        tuple(
            _assess(op, table, settings, observation, now)
            for op in MaintenanceOperation.ordered()
        )
    )


def _assess(
    op: MaintenanceOperation,
    table: Table,
    settings: MaintenanceSettings,
    observation: TableObservation,
    now: datetime,
) -> OperationAssessment:
    if not settings.enabled(op):
        return OperationAssessment(op, OperationVerdict.DISABLED)
    assessment = _measure(op, settings, observation, now)
    state = table.operation_state(op)
    if state.last_attempt_at is None:
        return assessment
    next_eligible_at = state.last_attempt_at + state.effective_cooldown(
        settings.min_interval(op)
    )
    if now >= next_eligible_at:
        return assessment
    return replace(
        assessment,
        verdict=OperationVerdict.COOLDOWN,
        next_eligible_at=next_eligible_at,
        planned=None,
    )


def _measure(
    op: MaintenanceOperation,
    settings: MaintenanceSettings,
    observation: TableObservation,
    now: datetime,
) -> OperationAssessment:
    match op:
        case MaintenanceOperation.REWRITE_DATA_FILES:
            return _assess_compaction(settings, observation)
        case MaintenanceOperation.REWRITE_MANIFESTS:
            return _assess_manifests(settings, observation)
        case MaintenanceOperation.EXPIRE_SNAPSHOTS:
            return _assess_snapshots(settings, observation, now)
        case MaintenanceOperation.REMOVE_ORPHAN_FILES:
            return OperationAssessment(
                op, OperationVerdict.DUE, planned=PlannedOperation(op)
            )


def _due(
    assessment: OperationAssessment, planned: PlannedOperation | None = None
) -> OperationAssessment:
    return replace(
        assessment,
        verdict=OperationVerdict.DUE,
        planned=PlannedOperation(assessment.operation) if planned is None else planned,
    )


def _assess_compaction(
    settings: MaintenanceSettings, observation: TableObservation
) -> OperationAssessment:
    cfg = settings.rewrite_data_files
    op = MaintenanceOperation.REWRITE_DATA_FILES
    target = resolve_target_file_size(cfg, observation.properties)
    if cfg.target_file_size_bytes is not None:
        source = SizeSource.SETTINGS
    elif positive_int_property(observation.properties, TARGET_FILE_SIZE_PROPERTY):
        source = SizeSource.TABLE_PROPERTY
    else:
        source = SizeSource.DEFAULT
    reducible = [
        (p, compute_reducible_files(p, target)) for p in observation.partitions
    ]
    base = OperationAssessment(
        op,
        OperationVerdict.NOT_DUE,
        threshold=cfg.min_reducible_files,
        size_bytes=target,
        size_source=source,
    )
    if cfg.scope == CompactionScope.TABLE:
        total = sum(r for _, r in reducible)
        assessment = replace(base, measured=total)
        return _due(assessment) if total >= cfg.min_reducible_files else assessment
    qualifying = [(p, r) for p, r in reducible if r >= cfg.min_reducible_files]
    assessment = replace(
        base,
        measured=sum(r for _, r in qualifying),
        qualifying_partitions=len(qualifying),
    )
    if not qualifying:
        return assessment
    selected = tuple(p for p, _ in qualifying)
    partitioned = {s.spec_id for s in observation.specs if not s.is_unpartitioned}
    if any(p.spec_id not in partitioned for p in selected):
        return _due(assessment)
    return _due(assessment, PlannedOperation(op, selected))


def _assess_manifests(
    settings: MaintenanceSettings, observation: TableObservation
) -> OperationAssessment:
    cfg = settings.rewrite_manifests
    prop = positive_int_property(observation.properties, MANIFEST_TARGET_SIZE_PROPERTY)
    if cfg.small_manifest_bytes is not None:
        threshold, source = cfg.small_manifest_bytes, SizeSource.SETTINGS
    elif prop is not None:
        threshold, source = prop, SizeSource.TABLE_PROPERTY
    else:
        threshold, source = DEFAULT_SMALL_MANIFEST_BYTES, SizeSource.DEFAULT
    small = sum(1 for m in observation.manifests if m.length_bytes < threshold)
    assessment = OperationAssessment(
        MaintenanceOperation.REWRITE_MANIFESTS,
        OperationVerdict.NOT_DUE,
        measured=small,
        threshold=cfg.min_small_manifests,
        size_bytes=threshold,
        size_source=source,
    )
    return _due(assessment) if small >= cfg.min_small_manifests else assessment


def _assess_snapshots(
    settings: MaintenanceSettings, observation: TableObservation, now: datetime
) -> OperationAssessment:
    cfg = settings.expire_snapshots
    newest_first = sorted(
        observation.snapshots, key=lambda s: s.committed_at, reverse=True
    )
    cutoff = now - cfg.older_than
    expirable = sum(
        1
        for s in newest_first[cfg.retain_last :]
        if s.committed_at < cutoff and s.snapshot_id != observation.current_snapshot_id
    )
    assessment = OperationAssessment(
        MaintenanceOperation.EXPIRE_SNAPSHOTS,
        OperationVerdict.NOT_DUE,
        measured=expirable,
        threshold=1,
    )
    return _due(assessment) if expirable >= 1 else assessment
