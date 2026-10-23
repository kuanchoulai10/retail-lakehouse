from __future__ import annotations

from datetime import UTC, datetime, timedelta

from application.domain.model.discovery import DiscoverySettings, DiscoverySettingsId

T0 = datetime(2026, 1, 1, tzinfo=UTC)
T1 = T0 + timedelta(minutes=1)


def test_default_singleton_enabled():
    s = DiscoverySettings.create(now=T0)
    assert s.id == DiscoverySettingsId("global")
    assert s.enabled


def test_disable_enable():
    s = DiscoverySettings.create(now=T0)
    s.disable(T1)
    assert not s.enabled
    assert s.updated_at == T1
    s.enable(T1 + timedelta(minutes=1))
    assert s.enabled
