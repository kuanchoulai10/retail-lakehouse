"""Define the MaintenanceSettingsCodec for the settings JSON column."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from application.port.outbound.table_maintenance_preset import (
    CompactionScope,
    ExpireSnapshotsSettings,
    MaintenanceSettings,
    RemoveOrphanFilesSettings,
    RewriteDataFilesSettings,
    RewriteManifestsSettings,
)


def _seconds(value: timedelta) -> int:
    if value % timedelta(seconds=1):
        raise ValueError(f"duration must be a whole number of seconds: {value!r}")
    return value // timedelta(seconds=1)


class MaintenanceSettingsCodec:
    """Convert MaintenanceSettings to and from a JSON-compatible dict.

    Durations are stored as integer seconds; encoding a duration that is not a
    whole number of seconds raises ``ValueError``.
    """

    @staticmethod
    def encode(settings: MaintenanceSettings) -> dict[str, Any]:
        """Return the JSON-compatible form of the settings."""
        rdf = settings.rewrite_data_files
        rm = settings.rewrite_manifests
        es = settings.expire_snapshots
        rof = settings.remove_orphan_files
        return {
            "reconcile_interval_seconds": _seconds(settings.reconcile_interval),
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

    @staticmethod
    def decode(data: dict[str, Any]) -> MaintenanceSettings:
        """Return the settings described by the JSON-compatible dict."""
        rdf = data["rewrite_data_files"]
        rm = data["rewrite_manifests"]
        es = data["expire_snapshots"]
        rof = data["remove_orphan_files"]
        return MaintenanceSettings(
            reconcile_interval=timedelta(seconds=data["reconcile_interval_seconds"]),
            rewrite_data_files=RewriteDataFilesSettings(
                enabled=rdf["enabled"],
                min_interval=timedelta(seconds=rdf["min_interval_seconds"]),
                scope=CompactionScope(rdf["scope"]),
                target_file_size_bytes=rdf["target_file_size_bytes"],
                min_reducible_files=rdf["min_reducible_files"],
            ),
            rewrite_manifests=RewriteManifestsSettings(
                enabled=rm["enabled"],
                min_interval=timedelta(seconds=rm["min_interval_seconds"]),
                min_small_manifests=rm["min_small_manifests"],
                small_manifest_bytes=rm["small_manifest_bytes"],
            ),
            expire_snapshots=ExpireSnapshotsSettings(
                enabled=es["enabled"],
                min_interval=timedelta(seconds=es["min_interval_seconds"]),
                older_than=timedelta(seconds=es["older_than_seconds"]),
                retain_last=es["retain_last"],
            ),
            remove_orphan_files=RemoveOrphanFilesSettings(
                enabled=rof["enabled"],
                min_interval=timedelta(seconds=rof["min_interval_seconds"]),
                older_than=timedelta(seconds=rof["older_than_seconds"]),
            ),
        )
