from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Engine

from adapter.outbound.table_discovery_settings.sql import TableDiscoverySettingsSqlRepo
from application.exceptions import ConflictError
from application.domain.model.table_discovery_settings import (
    GLOBAL_ID,
    TableDiscoverySettings,
)

NOW = datetime(2026, 10, 24, tzinfo=UTC)


@pytest.fixture
def repo(engine: Engine) -> TableDiscoverySettingsSqlRepo:
    return TableDiscoverySettingsSqlRepo(engine)


def test_get_settings_on_empty_db_is_enabled(repo: TableDiscoverySettingsSqlRepo):
    settings = repo.get_settings()
    assert settings.enabled is True
    assert settings.id == GLOBAL_ID
    assert settings.updated_at.tzinfo is not None
    assert repo.list_all() == []


def test_save_inserts_then_replaces(repo: TableDiscoverySettingsSqlRepo):
    settings = TableDiscoverySettings.create(NOW, enabled=True)
    settings.disable(NOW)
    repo.save(settings)
    loaded = repo.get_settings()
    assert loaded.enabled is False
    assert loaded.updated_at == NOW
    assert loaded.updated_at.tzinfo is not None

    later = NOW + timedelta(hours=1)
    settings.enable(later)
    repo.save(settings)
    loaded = repo.get_settings()
    assert loaded.enabled is True
    assert loaded.updated_at == later
    assert len(repo.list_all()) == 1
    assert loaded.collect_events() == []


def test_create_and_get(repo: TableDiscoverySettingsSqlRepo):
    repo.create(TableDiscoverySettings.create(NOW, enabled=False))
    loaded = repo.get(GLOBAL_ID)
    assert loaded is not None
    assert loaded.enabled is False
    assert repo.get(GLOBAL_ID.__class__("other")) is None


def test_create_duplicate_primary_key_raises_conflict(
    repo: TableDiscoverySettingsSqlRepo,
):
    repo.create(TableDiscoverySettings.create(NOW))
    with pytest.raises(ConflictError):
        repo.create(TableDiscoverySettings.create(NOW))
