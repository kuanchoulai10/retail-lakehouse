"""Define the maintenance_procedure_args function."""

from __future__ import annotations

from datetime import UTC
from typing import TYPE_CHECKING, Any

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
)
from context.table_maintenance.application.domain.service.shared import (
    DEFAULT_ORPHAN_OLDER_THAN,
    resolve_snapshot_retention,
    resolve_target_file_size,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime, timedelta

    from context.table_maintenance.application.domain.model.table_maintenance_policy import (
        MaintenancePolicyContent,
    )


def maintenance_procedure_args(
    operation: MaintenanceOperation,
    policy: MaintenancePolicyContent,
    properties: Mapping[str, str],
    now: datetime,
) -> dict[str, Any]:
    """Return the primitive Iceberg procedure arguments of one operation, from its target and options.

    Only the options that are set are present, under the procedure's own names; ``rewrite_data_files``
    carries its options map under ``options`` in Iceberg's spelling, with the table's target file size.
    An operation the policy leaves out (a manual run of it) runs with what the platform decides: the
    target file size alone, no manifest options, the retention of the table's properties and Iceberg's
    defaults, and orphan files older than 3 days. ``now`` must be timezone-aware; ``older_than`` is
    ``now`` minus the age, rendered as ISO-8601 with a ``+00:00`` offset.
    """
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    match operation:
        case MaintenanceOperation.REWRITE_DATA_FILES:
            return _rewrite_data_files_args(policy, properties)
        case MaintenanceOperation.REWRITE_MANIFESTS:
            return _rewrite_manifests_args(policy)
        case MaintenanceOperation.EXPIRE_SNAPSHOTS:
            return _expire_snapshots_args(policy, properties, now)
        case MaintenanceOperation.REMOVE_ORPHAN_FILES:
            return _remove_orphan_files_args(policy, now)


def _rewrite_data_files_args(policy: MaintenancePolicyContent, properties: Mapping[str, str]) -> dict[str, Any]:
    rewrite = policy.rewrite_data_files
    options = None if rewrite is None else rewrite.options
    procedure_options: dict[str, Any] = {"target-file-size-bytes": resolve_target_file_size(properties)}
    if options is None:
        return {"options": procedure_options}
    return {**options.procedure_arguments(), "options": {**procedure_options, **options.procedure_options()}}


def _rewrite_manifests_args(policy: MaintenancePolicyContent) -> dict[str, Any]:
    manifests = policy.rewrite_manifests
    if manifests is None or manifests.options is None:
        return {}
    return dict(manifests.options.procedure_arguments())


def _expire_snapshots_args(
    policy: MaintenancePolicyContent, properties: Mapping[str, str], now: datetime
) -> dict[str, Any]:
    snapshots = policy.expire_snapshots
    retention = resolve_snapshot_retention(None if snapshots is None else snapshots.target, properties)
    args: dict[str, Any] = {
        "older_than": _older_than(now, retention.max_snapshot_age),
        "retain_last": retention.min_snapshots_to_keep,
    }
    if snapshots is not None and snapshots.options is not None:
        args.update(snapshots.options.procedure_arguments())
    return args


def _remove_orphan_files_args(policy: MaintenancePolicyContent, now: datetime) -> dict[str, Any]:
    orphans = policy.remove_orphan_files
    if orphans is None:
        return {"older_than": _older_than(now, DEFAULT_ORPHAN_OLDER_THAN)}
    args: dict[str, Any] = {"older_than": _older_than(now, orphans.target.older_than)}
    if orphans.options is not None:
        args.update(orphans.options.procedure_arguments())
    return args


def _older_than(now: datetime, age: timedelta) -> str:
    return (now - age).astimezone(UTC).isoformat()
