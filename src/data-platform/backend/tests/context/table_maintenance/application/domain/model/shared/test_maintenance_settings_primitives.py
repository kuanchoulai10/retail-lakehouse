"""Test the wire form of maintenance settings, shared by the REST API and the settings JSON column.

``GOLDEN`` and ``GOLDEN_CUSTOM`` were copied literally from the output of
``MaintenanceSettingsCodec.encode`` (and the identical
``maintenance_settings_to_dict``) before both were retired, so rows already
stored in PostgreSQL and REST bodies keep their exact shape and key order.
"""

from __future__ import annotations

import json
from datetime import timedelta
from typing import TYPE_CHECKING, Any

import pytest

from base.model import validation_message
from context.table_maintenance.application.domain.model.shared import (
    CompactionScope,
    ExpireSnapshotsSettings,
    MaintenanceSettings,
    RemoveOrphanFilesSettings,
    RewriteDataFilesSettings,
    RewriteManifestsSettings,
)

if TYPE_CHECKING:
    from collections.abc import Callable

GOLDEN: dict[str, Any] = {
    "reconcile_interval_seconds": 3600,
    "dry_run": False,
    "rewrite_data_files": {
        "enabled": True,
        "min_interval_seconds": 3600,
        "scope": "partition",
        "target_file_size_bytes": None,
        "min_reducible_files": 5,
    },
    "rewrite_manifests": {
        "enabled": True,
        "min_interval_seconds": 21600,
        "min_small_manifests": 5,
        "small_manifest_bytes": None,
    },
    "expire_snapshots": {
        "enabled": True,
        "min_interval_seconds": 21600,
        "older_than_seconds": 86400,
        "retain_last": 10,
    },
    "remove_orphan_files": {
        "enabled": True,
        "min_interval_seconds": 604800,
        "older_than_seconds": 259200,
    },
}

GOLDEN_CUSTOM: dict[str, Any] = {
    "reconcile_interval_seconds": 1800,
    "dry_run": True,
    "rewrite_data_files": {
        "enabled": False,
        "min_interval_seconds": 7200,
        "scope": "table",
        "target_file_size_bytes": 134217728,
        "min_reducible_files": 7,
    },
    "rewrite_manifests": {
        "enabled": False,
        "min_interval_seconds": 43200,
        "min_small_manifests": 9,
        "small_manifest_bytes": 4194304,
    },
    "expire_snapshots": {
        "enabled": False,
        "min_interval_seconds": 10800,
        "older_than_seconds": 172800,
        "retain_last": 4,
    },
    "remove_orphan_files": {
        "enabled": False,
        "min_interval_seconds": 1209600,
        "older_than_seconds": 432000,
    },
}


def _custom() -> MaintenanceSettings:
    """Return the settings GOLDEN_CUSTOM was encoded from."""
    return MaintenanceSettings(
        reconcile_interval=timedelta(minutes=30),
        dry_run=True,
        rewrite_data_files=RewriteDataFilesSettings(
            enabled=False,
            min_interval=timedelta(hours=2),
            scope=CompactionScope.TABLE,
            target_file_size_bytes=134217728,
            min_reducible_files=7,
        ),
        rewrite_manifests=RewriteManifestsSettings(
            enabled=False,
            min_interval=timedelta(hours=12),
            min_small_manifests=9,
            small_manifest_bytes=4194304,
        ),
        expire_snapshots=ExpireSnapshotsSettings(
            enabled=False,
            min_interval=timedelta(hours=3),
            older_than=timedelta(days=2),
            retain_last=4,
        ),
        remove_orphan_files=RemoveOrphanFilesSettings(
            enabled=False,
            min_interval=timedelta(days=14),
            older_than=timedelta(days=5),
        ),
    )


def test_defaults_encode_to_golden() -> None:
    """The default settings encode to exactly the stored shape, key order included."""
    encoded = MaintenanceSettings().to_primitives()
    assert encoded == GOLDEN
    assert json.dumps(encoded) == json.dumps(GOLDEN)


def test_custom_encodes_to_golden() -> None:
    """Settings with every field changed encode to exactly the stored shape."""
    encoded = _custom().to_primitives()
    assert encoded == GOLDEN_CUSTOM
    assert json.dumps(encoded) == json.dumps(GOLDEN_CUSTOM)


def test_golden_decodes_to_the_settings_it_was_encoded_from() -> None:
    """Stored rows decode to the same settings the retired codec wrote them from."""
    assert MaintenanceSettings.from_primitives(GOLDEN) == MaintenanceSettings()
    assert MaintenanceSettings.from_primitives(GOLDEN_CUSTOM) == _custom()


def test_custom_round_trips() -> None:
    """A stored row decodes and re-encodes to the same JSON."""
    encoded = MaintenanceSettings.from_primitives(GOLDEN_CUSTOM).to_primitives()
    assert json.dumps(encoded) == json.dumps(GOLDEN_CUSTOM)


def test_empty_input_takes_defaults() -> None:
    """An empty object is the default settings."""
    assert MaintenanceSettings.from_primitives({}) == MaintenanceSettings()


def test_partial_input_takes_defaults() -> None:
    """Fields left out take their defaults, a row without ``dry_run`` included."""
    assert MaintenanceSettings.from_primitives({"dry_run": True}) == MaintenanceSettings(dry_run=True)
    without_dry_run = {key: value for key, value in GOLDEN_CUSTOM.items() if key != "dry_run"}
    assert MaintenanceSettings.from_primitives(without_dry_run).dry_run is False


def test_partial_section_overrides_only_given_fields() -> None:
    """A partial section overrides only the fields it names."""
    settings = MaintenanceSettings.from_primitives(
        {
            "reconcile_interval_seconds": 7200,
            "rewrite_data_files": {"scope": "table", "min_reducible_files": 9},
            "expire_snapshots": {"older_than_seconds": 3600, "enabled": False},
        }
    )
    assert settings.reconcile_interval == timedelta(hours=2)
    assert settings.rewrite_data_files == RewriteDataFilesSettings(scope=CompactionScope.TABLE, min_reducible_files=9)
    assert settings.expire_snapshots == ExpireSnapshotsSettings(older_than=timedelta(hours=1), enabled=False)
    assert settings.remove_orphan_files == RemoveOrphanFilesSettings()


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"dry_run": 1}, "dry_run: Input should be a valid boolean"),
        ({"dry_run": "yes"}, "dry_run: Input should be a valid boolean"),
        (
            {"rewrite_data_files": {"min_reducible_files": True}},
            "rewrite_data_files.min_reducible_files: Input should be a valid integer",
        ),
        ({"unknown": 1}, "unknown: Extra inputs are not permitted"),
        ({"rewrite_data_files": {"foo": 1}}, "rewrite_data_files.foo: Extra inputs are not permitted"),
        ({"reconcile_interval_seconds": 0}, "reconcile_interval_seconds: must be positive"),
        (
            {"reconcile_interval_seconds": 1.5},
            "reconcile_interval_seconds: must be a timedelta or a whole number of seconds",
        ),
        (
            {"remove_orphan_files": {"older_than_seconds": 3600}},
            "remove_orphan_files.older_than_seconds: must be at least 1 day",
        ),
        (
            {"expire_snapshots": {"retain_last": 0}},
            "expire_snapshots.retain_last: Input should be greater than 0",
        ),
        (
            {"rewrite_manifests": {"small_manifest_bytes": 0}},
            "rewrite_manifests.small_manifest_bytes: Input should be greater than 0",
        ),
        ({"rewrite_data_files": "nope"}, "rewrite_data_files: Input should be an object"),
        (
            {"rewrite_data_files": {"scope": "galaxy"}},
            "rewrite_data_files.scope: Input should be 'partition' or 'table'",
        ),
    ],
)
def test_invalid_input_names_the_field(data: dict[str, Any], message: str) -> None:
    """Invalid input raises a ValueError whose one-line message names the field."""
    with pytest.raises(ValueError) as caught:
        MaintenanceSettings.from_primitives(data)
    assert validation_message(caught.value) == message


@pytest.mark.parametrize(
    "build",
    [
        lambda: MaintenanceSettings(reconcile_interval=timedelta(seconds=1, milliseconds=500)),
        lambda: MaintenanceSettings(
            expire_snapshots=ExpireSnapshotsSettings(older_than=timedelta(days=1, microseconds=1))
        ),
    ],
)
def test_non_whole_second_duration_fails_to_encode(build: Callable[[], MaintenanceSettings]) -> None:
    """A duration that is not a whole number of seconds cannot be written."""
    with pytest.raises(ValueError, match="whole number of seconds"):
        build().to_primitives()
