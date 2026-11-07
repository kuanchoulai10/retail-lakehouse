from __future__ import annotations

from datetime import UTC, datetime, timedelta

from context.table_maintenance.application.domain.model.table_discovery_settings import (
    TableDiscoverySettings,
    TableDiscoverySettingsId,
)

T0 = datetime(2026, 1, 1, tzinfo=UTC)
T1 = T0 + timedelta(minutes=1)


def test_default_singleton_enabled():
    s = TableDiscoverySettings.create(now=T0)
    assert s.id == TableDiscoverySettingsId("global")
    assert s.enabled


def test_disable_enable():
    s = TableDiscoverySettings.create(now=T0)
    s.disable(T1)
    assert not s.enabled
    assert s.updated_at == T1
    s.enable(T1 + timedelta(minutes=1))
    assert s.enabled
