from __future__ import annotations

import json
from datetime import timedelta

import pytest

from adapter.outbound.shared.sql.maintenance_settings_codec import (
    MaintenanceSettingsCodec,
)
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


def test_default_settings_roundtrip():
    settings = MaintenanceSettings()
    encoded = MaintenanceSettingsCodec.encode(settings)
    assert MaintenanceSettingsCodec.decode(json.loads(json.dumps(encoded))) == settings


def test_custom_settings_roundtrip_with_second_integer_durations():
    settings = MaintenanceSettings(
        reconcile_interval=timedelta(minutes=30),
        rewrite_data_files=RewriteDataFilesSettings(
            enabled=False,
            min_interval=timedelta(hours=2),
            scope=CompactionScope.TABLE,
            target_file_size_bytes=536870912,
            min_reducible_files=9,
        ),
        rewrite_manifests=RewriteManifestsSettings(
            min_small_manifests=3, small_manifest_bytes=1024
        ),
        expire_snapshots=ExpireSnapshotsSettings(
            older_than=timedelta(days=2), retain_last=4
        ),
        remove_orphan_files=RemoveOrphanFilesSettings(older_than=timedelta(days=5)),
    )
    encoded = MaintenanceSettingsCodec.encode(settings)
    assert encoded["reconcile_interval_seconds"] == 1800
    assert encoded["remove_orphan_files"]["older_than_seconds"] == 5 * 86400
    assert MaintenanceSettingsCodec.decode(json.loads(json.dumps(encoded))) == settings


def test_encode_rejects_sub_second_duration():
    with pytest.raises(ValueError, match="whole number of seconds"):
        MaintenanceSettingsCodec.encode(
            MaintenanceSettings(
                reconcile_interval=timedelta(seconds=1, milliseconds=500)
            )
        )
    with pytest.raises(ValueError, match="whole number of seconds"):
        MaintenanceSettingsCodec.encode(
            MaintenanceSettings(
                expire_snapshots=ExpireSnapshotsSettings(
                    older_than=timedelta(days=1, microseconds=1)
                )
            )
        )
