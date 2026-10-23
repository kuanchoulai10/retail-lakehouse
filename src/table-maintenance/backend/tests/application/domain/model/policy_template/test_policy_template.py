from __future__ import annotations

from datetime import UTC, datetime, timedelta

from application.domain.model.maintenance_settings import MaintenanceSettings
from application.domain.model.policy_template import PolicyTemplate, PolicyTemplateId

T0 = datetime(2026, 1, 1, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)


def make() -> PolicyTemplate:
    return PolicyTemplate.create(
        id=PolicyTemplateId("t1"),
        name="default",
        settings=MaintenanceSettings(),
        now=T0,
    )


def test_create():
    t = make()
    assert t.id == PolicyTemplateId("t1")
    assert t.name == "default"
    assert t.created_at == T0
    assert t.updated_at == T0


def test_rename_and_update_settings():
    t = make()
    t.rename("other", T1)
    assert t.name == "other"
    assert t.updated_at == T1
    new = MaintenanceSettings(reconcile_interval=timedelta(hours=2))
    t.update_settings(new, T1 + timedelta(hours=1))
    assert t.settings == new
    assert t.updated_at == T1 + timedelta(hours=1)
    assert t.created_at == T0
