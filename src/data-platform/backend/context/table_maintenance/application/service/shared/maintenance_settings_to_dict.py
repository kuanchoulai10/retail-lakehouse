"""Define the maintenance_settings_to_dict function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import timedelta

    from context.table_maintenance.application.domain.model.shared import (
        MaintenanceSettings,
    )


def _seconds(value: timedelta) -> int:
    return int(value.total_seconds())


def maintenance_settings_to_dict(settings: MaintenanceSettings) -> dict[str, Any]:
    """Return the primitive dict form of the settings, durations in seconds."""
    rdf = settings.rewrite_data_files
    rm = settings.rewrite_manifests
    es = settings.expire_snapshots
    rof = settings.remove_orphan_files
    return {
        "reconcile_interval_seconds": _seconds(settings.reconcile_interval),
        "dry_run": settings.dry_run,
        "rewrite_data_files": {
            "enabled": rdf.enabled,
            "min_interval_seconds": _seconds(rdf.min_interval),
            "scope": rdf.scope.value,
            "target_file_size_bytes": rdf.target_file_size_bytes,
            "min_reducible_files": rdf.min_reducible_files,
        },
        "rewrite_manifests": {
            "enabled": rm.enabled,
            "min_interval_seconds": _seconds(rm.min_interval),
            "min_small_manifests": rm.min_small_manifests,
            "small_manifest_bytes": rm.small_manifest_bytes,
        },
        "expire_snapshots": {
            "enabled": es.enabled,
            "min_interval_seconds": _seconds(es.min_interval),
            "older_than_seconds": _seconds(es.older_than),
            "retain_last": es.retain_last,
        },
        "remove_orphan_files": {
            "enabled": rof.enabled,
            "min_interval_seconds": _seconds(rof.min_interval),
            "older_than_seconds": _seconds(rof.older_than),
        },
    }
