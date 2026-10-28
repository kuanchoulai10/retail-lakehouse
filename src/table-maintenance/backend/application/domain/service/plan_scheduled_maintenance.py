"""Define the plan_scheduled_maintenance domain service."""

from __future__ import annotations

from datetime import datetime

from application.domain.model.maintenance.maintenance_operation import (
    MaintenanceOperation,
)
from application.domain.model.maintenance.maintenance_plan import MaintenancePlan
from application.domain.model.maintenance.planned_operation import PlannedOperation
from application.domain.model.maintenance_settings.compaction_scope import (
    CompactionScope,
)
from application.domain.model.maintenance_settings.maintenance_settings import (
    MaintenanceSettings,
)
from application.domain.model.table.table import Table
from application.domain.model.table.table_status import TableStatus
from application.domain.model.observation.table_observation import TableObservation
from application.domain.service.compute_reducible_files import compute_reducible_files
from application.domain.service.positive_int_property import positive_int_property
from application.domain.service.resolve_target_file_size import (
    resolve_target_file_size,
)

DEFAULT_SMALL_MANIFEST_BYTES = 8 * 1024 * 1024
MANIFEST_TARGET_SIZE_PROPERTY = "commit.manifest.target-size-bytes"


def plan_scheduled_maintenance(
    table: Table, observation: TableObservation, now: datetime
) -> MaintenancePlan:
    """Decide which operations are due for a table given its observation."""
    settings = table.settings
    if table.status != TableStatus.ACTIVE or settings is None:
        return MaintenancePlan()
    planned: list[PlannedOperation] = []
    for op in MaintenanceOperation.ordered():
        if not settings.enabled(op) or _in_cooldown(table, settings, op, now):
            continue
        planned_op = _plan_operation(op, settings, observation, now)
        if planned_op is not None:
            planned.append(planned_op)
    return MaintenancePlan(tuple(planned))


def _in_cooldown(
    table: Table,
    settings: MaintenanceSettings,
    op: MaintenanceOperation,
    now: datetime,
) -> bool:
    state = table.operation_state(op)
    if state.last_attempt_at is None:
        return False
    cooldown = state.effective_cooldown(settings.min_interval(op))
    return now - state.last_attempt_at < cooldown


def _plan_operation(
    op: MaintenanceOperation,
    settings: MaintenanceSettings,
    observation: TableObservation,
    now: datetime,
) -> PlannedOperation | None:
    match op:
        case MaintenanceOperation.REWRITE_DATA_FILES:
            return _plan_compaction(settings, observation)
        case MaintenanceOperation.REWRITE_MANIFESTS:
            due = _manifests_due(settings, observation)
        case MaintenanceOperation.EXPIRE_SNAPSHOTS:
            due = _snapshots_due(settings, observation, now)
        case MaintenanceOperation.REMOVE_ORPHAN_FILES:
            due = True
    return PlannedOperation(op) if due else None


def _plan_compaction(
    settings: MaintenanceSettings, observation: TableObservation
) -> PlannedOperation | None:
    cfg = settings.rewrite_data_files
    target = resolve_target_file_size(cfg, observation.properties)
    op = MaintenanceOperation.REWRITE_DATA_FILES
    reducible = [
        (p, compute_reducible_files(p, target)) for p in observation.partitions
    ]
    if cfg.scope == CompactionScope.TABLE:
        total = sum(r for _, r in reducible)
        return PlannedOperation(op) if total >= cfg.min_reducible_files else None
    selected = tuple(p for p, r in reducible if r >= cfg.min_reducible_files)
    if not selected:
        return None
    partitioned = {s.spec_id for s in observation.specs if not s.is_unpartitioned}
    if any(p.spec_id not in partitioned for p in selected):
        return PlannedOperation(op)
    return PlannedOperation(op, selected)


def _manifests_due(
    settings: MaintenanceSettings, observation: TableObservation
) -> bool:
    cfg = settings.rewrite_manifests
    threshold = (
        cfg.small_manifest_bytes
        or positive_int_property(observation.properties, MANIFEST_TARGET_SIZE_PROPERTY)
        or DEFAULT_SMALL_MANIFEST_BYTES
    )
    small = sum(1 for m in observation.manifests if m.length_bytes < threshold)
    return small >= cfg.min_small_manifests


def _snapshots_due(
    settings: MaintenanceSettings, observation: TableObservation, now: datetime
) -> bool:
    cfg = settings.expire_snapshots
    newest_first = sorted(
        observation.snapshots, key=lambda s: s.committed_at, reverse=True
    )
    cutoff = now - cfg.older_than
    return any(
        s.committed_at < cutoff and s.snapshot_id != observation.current_snapshot_id
        for s in newest_first[cfg.retain_last :]
    )
