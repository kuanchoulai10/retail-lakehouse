"""Define the maintenance_settings_from_dict function."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any

from application.domain.model.shared.compaction_scope import (
    CompactionScope,
)
from application.domain.model.shared.expire_snapshots_settings import (
    ExpireSnapshotsSettings,
)
from application.domain.model.shared.maintenance_settings import (
    MaintenanceSettings,
)
from application.domain.model.shared.remove_orphan_files_settings import (
    RemoveOrphanFilesSettings,
)
from application.domain.model.shared.rewrite_data_files_settings import (
    RewriteDataFilesSettings,
)
from application.domain.model.shared.rewrite_manifests_settings import (
    RewriteManifestsSettings,
)
from application.exceptions import ValidationError

if TYPE_CHECKING:
    from collections.abc import Mapping

_ROOT_KEYS = {
    "reconcile_interval_seconds",
    "rewrite_data_files",
    "rewrite_manifests",
    "expire_snapshots",
    "remove_orphan_files",
}


def _check_keys(data: Mapping[str, Any], allowed: set[str], where: str) -> None:
    unknown = set(data) - allowed
    if unknown:
        raise ValidationError(f"unknown keys in {where}: {sorted(unknown)}")


def _section(data: Mapping[str, Any], name: str, allowed: set[str]) -> dict[str, Any]:
    section = data.get(name, {})
    if not isinstance(section, dict):
        raise ValidationError(f"{name} must be an object")
    _check_keys(section, allowed, name)
    return section


def _int(value: Any, name: str) -> int:  # noqa: ANN401
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{name} must be an integer")
    return value


def _optional_int(value: Any, name: str) -> int | None:  # noqa: ANN401
    return None if value is None else _int(value, name)


def _bool(value: Any, name: str) -> bool:  # noqa: ANN401
    if not isinstance(value, bool):
        raise ValidationError(f"{name} must be a boolean")
    return value


def _seconds(value: Any, name: str) -> timedelta:  # noqa: ANN401
    return timedelta(seconds=_int(value, name))


def _rewrite_data_files(data: Mapping[str, Any]) -> RewriteDataFilesSettings:
    d = RewriteDataFilesSettings()
    s = _section(
        data,
        "rewrite_data_files",
        {
            "enabled",
            "min_interval_seconds",
            "scope",
            "target_file_size_bytes",
            "min_reducible_files",
        },
    )
    return RewriteDataFilesSettings(
        enabled=_bool(s["enabled"], "enabled") if "enabled" in s else d.enabled,
        min_interval=(
            _seconds(s["min_interval_seconds"], "min_interval_seconds")
            if "min_interval_seconds" in s
            else d.min_interval
        ),
        scope=CompactionScope(s["scope"]) if "scope" in s else d.scope,
        target_file_size_bytes=(
            _optional_int(s["target_file_size_bytes"], "target_file_size_bytes")
            if "target_file_size_bytes" in s
            else d.target_file_size_bytes
        ),
        min_reducible_files=(
            _int(s["min_reducible_files"], "min_reducible_files")
            if "min_reducible_files" in s
            else d.min_reducible_files
        ),
    )


def _rewrite_manifests(data: Mapping[str, Any]) -> RewriteManifestsSettings:
    d = RewriteManifestsSettings()
    s = _section(
        data,
        "rewrite_manifests",
        {
            "enabled",
            "min_interval_seconds",
            "min_small_manifests",
            "small_manifest_bytes",
        },
    )
    return RewriteManifestsSettings(
        enabled=_bool(s["enabled"], "enabled") if "enabled" in s else d.enabled,
        min_interval=(
            _seconds(s["min_interval_seconds"], "min_interval_seconds")
            if "min_interval_seconds" in s
            else d.min_interval
        ),
        min_small_manifests=(
            _int(s["min_small_manifests"], "min_small_manifests")
            if "min_small_manifests" in s
            else d.min_small_manifests
        ),
        small_manifest_bytes=(
            _optional_int(s["small_manifest_bytes"], "small_manifest_bytes")
            if "small_manifest_bytes" in s
            else d.small_manifest_bytes
        ),
    )


def _expire_snapshots(data: Mapping[str, Any]) -> ExpireSnapshotsSettings:
    d = ExpireSnapshotsSettings()
    s = _section(
        data,
        "expire_snapshots",
        {"enabled", "min_interval_seconds", "older_than_seconds", "retain_last"},
    )
    return ExpireSnapshotsSettings(
        enabled=_bool(s["enabled"], "enabled") if "enabled" in s else d.enabled,
        min_interval=(
            _seconds(s["min_interval_seconds"], "min_interval_seconds")
            if "min_interval_seconds" in s
            else d.min_interval
        ),
        older_than=(
            _seconds(s["older_than_seconds"], "older_than_seconds")
            if "older_than_seconds" in s
            else d.older_than
        ),
        retain_last=(
            _int(s["retain_last"], "retain_last")
            if "retain_last" in s
            else d.retain_last
        ),
    )


def _remove_orphan_files(data: Mapping[str, Any]) -> RemoveOrphanFilesSettings:
    d = RemoveOrphanFilesSettings()
    s = _section(
        data,
        "remove_orphan_files",
        {"enabled", "min_interval_seconds", "older_than_seconds"},
    )
    return RemoveOrphanFilesSettings(
        enabled=_bool(s["enabled"], "enabled") if "enabled" in s else d.enabled,
        min_interval=(
            _seconds(s["min_interval_seconds"], "min_interval_seconds")
            if "min_interval_seconds" in s
            else d.min_interval
        ),
        older_than=(
            _seconds(s["older_than_seconds"], "older_than_seconds")
            if "older_than_seconds" in s
            else d.older_than
        ),
    )


def maintenance_settings_from_dict(data: Mapping[str, Any]) -> MaintenanceSettings:
    """Build settings from a primitive dict; missing fields take domain defaults.

    Raise ValidationError for unknown keys, wrong types or invariant violations.
    """
    _check_keys(data, _ROOT_KEYS, "settings")
    default = MaintenanceSettings()
    try:
        return MaintenanceSettings(
            reconcile_interval=(
                _seconds(
                    data["reconcile_interval_seconds"], "reconcile_interval_seconds"
                )
                if "reconcile_interval_seconds" in data
                else default.reconcile_interval
            ),
            rewrite_data_files=_rewrite_data_files(data),
            rewrite_manifests=_rewrite_manifests(data),
            expire_snapshots=_expire_snapshots(data),
            remove_orphan_files=_remove_orphan_files(data),
        )
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
