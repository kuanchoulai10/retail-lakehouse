"""Test the maintenance settings value object, its defaults and its validation."""

from __future__ import annotations

from datetime import timedelta

import pytest
from pydantic import ValidationError

from context.table_maintenance.application.domain.model.shared import (
    CompactionScope,
    ExpireSnapshotsSettings,
    MaintenanceOperation,
    MaintenanceSettings,
    RemoveOrphanFilesSettings,
    RewriteDataFilesSettings,
    RewriteManifestsSettings,
)


def test_defaults():
    """The default settings reconcile hourly and compact by partition."""
    s = MaintenanceSettings()
    assert s.reconcile_interval == timedelta(hours=1)
    assert s.rewrite_data_files == RewriteDataFilesSettings()
    assert s.rewrite_data_files.scope == CompactionScope.PARTITION
    assert s.rewrite_data_files.min_interval == timedelta(hours=1)
    assert s.rewrite_data_files.min_reducible_files == 5
    assert s.rewrite_data_files.target_file_size_bytes is None
    assert s.rewrite_manifests.min_interval == timedelta(hours=6)
    assert s.rewrite_manifests.min_small_manifests == 5
    assert s.rewrite_manifests.small_manifest_bytes is None
    assert s.expire_snapshots.older_than == timedelta(days=1)
    assert s.expire_snapshots.retain_last == 10
    assert s.remove_orphan_files.min_interval == timedelta(days=7)
    assert s.remove_orphan_files.older_than == timedelta(days=3)


def test_for_operation_min_interval_and_enabled():
    """Settings answer the per-operation settings, minimum interval and enabled flag."""
    s = MaintenanceSettings(expire_snapshots=ExpireSnapshotsSettings(enabled=False, min_interval=timedelta(hours=2)))
    for op in MaintenanceOperation:
        assert s.for_operation(op) is getattr(s, op.value)
    assert s.min_interval(MaintenanceOperation.EXPIRE_SNAPSHOTS) == timedelta(hours=2)
    assert s.enabled(MaintenanceOperation.EXPIRE_SNAPSHOTS) is False
    assert s.enabled(MaintenanceOperation.REWRITE_DATA_FILES) is True


def test_remove_orphan_files_older_than_below_one_day_rejected():
    """An orphan file retention below one day is rejected."""
    with pytest.raises(ValidationError):
        RemoveOrphanFilesSettings(older_than=timedelta(hours=23))
    RemoveOrphanFilesSettings(older_than=timedelta(days=1))


def test_non_positive_intervals_rejected():
    """An interval that is zero or negative is rejected."""
    zero = timedelta(0)
    bad = [
        lambda: MaintenanceSettings(reconcile_interval=zero),
        lambda: RewriteDataFilesSettings(min_interval=zero),
        lambda: RewriteManifestsSettings(min_interval=zero),
        lambda: ExpireSnapshotsSettings(min_interval=zero),
        lambda: RemoveOrphanFilesSettings(min_interval=zero),
        lambda: ExpireSnapshotsSettings(older_than=zero),
        lambda: ExpireSnapshotsSettings(retain_last=0),
        lambda: RewriteDataFilesSettings(min_reducible_files=0),
        lambda: RewriteDataFilesSettings(target_file_size_bytes=0),
        lambda: RewriteManifestsSettings(min_small_manifests=0),
        lambda: RewriteManifestsSettings(small_manifest_bytes=0),
    ]
    for make in bad:
        with pytest.raises(ValidationError):
            make()


def test_invalid_settings_error_is_a_value_error():
    """A broken invariant raises a ValueError, which the application maps to a validation error."""
    with pytest.raises(ValueError, match="must be positive"):
        ExpireSnapshotsSettings(min_interval=timedelta(0))
