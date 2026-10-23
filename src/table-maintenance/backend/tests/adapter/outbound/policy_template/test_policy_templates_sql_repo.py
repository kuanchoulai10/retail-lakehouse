from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError

from adapter.outbound.policy_template.sql.policy_templates_sql_repo import (
    PolicyTemplatesSqlRepo,
)
from application.domain.model.maintenance_settings.maintenance_settings import (
    MaintenanceSettings,
)
from application.domain.model.policy_template.policy_template import PolicyTemplate
from application.domain.model.policy_template.policy_template_id import (
    PolicyTemplateId,
)

NOW = datetime(2026, 10, 24, tzinfo=UTC)


def _template(template_id: str, name: str) -> PolicyTemplate:
    return PolicyTemplate.create(
        PolicyTemplateId(template_id),
        name,
        MaintenanceSettings(reconcile_interval=timedelta(minutes=20)),
        NOW,
    )


@pytest.fixture
def repo(engine: Engine) -> PolicyTemplatesSqlRepo:
    return PolicyTemplatesSqlRepo(engine)


def test_roundtrip(repo: PolicyTemplatesSqlRepo):
    original = _template("t1", "default")
    repo.create(original)
    loaded = repo.get(PolicyTemplateId("t1"))
    assert loaded is not None
    assert loaded.name == "default"
    assert loaded.settings == original.settings
    assert loaded.created_at == NOW
    assert loaded.created_at.tzinfo is not None
    assert loaded.updated_at == NOW
    assert loaded.collect_events() == []


def test_get_missing_returns_none(repo: PolicyTemplatesSqlRepo):
    assert repo.get(PolicyTemplateId("nope")) is None


def test_update_persists(repo: PolicyTemplatesSqlRepo):
    template = _template("t1", "default")
    repo.create(template)
    later = NOW + timedelta(days=1)
    template.rename("renamed", later)
    template.update_settings(MaintenanceSettings(), later)
    repo.update(template)
    loaded = repo.get(template.id)
    assert loaded is not None
    assert loaded.name == "renamed"
    assert loaded.settings == MaintenanceSettings()
    assert loaded.updated_at == later


def test_update_missing_raises(repo: PolicyTemplatesSqlRepo):
    with pytest.raises(LookupError):
        repo.update(_template("ghost", "ghost"))


def test_name_is_unique(repo: PolicyTemplatesSqlRepo):
    repo.create(_template("t1", "default"))
    with pytest.raises(IntegrityError):
        repo.create(_template("t2", "default"))


def test_find_by_name_exact(repo: PolicyTemplatesSqlRepo):
    repo.create(_template("t1", "default"))
    found = repo.find_by_name("default")
    assert found is not None
    assert found.id == PolicyTemplateId("t1")
    assert repo.find_by_name("Default") is None
    assert repo.find_by_name("defaul") is None


def test_delete(repo: PolicyTemplatesSqlRepo):
    repo.create(_template("t1", "default"))
    repo.delete(PolicyTemplateId("t1"))
    assert repo.get(PolicyTemplateId("t1")) is None


def test_list_all_ordered_by_name(repo: PolicyTemplatesSqlRepo):
    repo.create(_template("1", "zeta"))
    repo.create(_template("2", "alpha"))
    repo.create(_template("3", "mid"))
    assert [t.name for t in repo.list_all()] == ["alpha", "mid", "zeta"]
