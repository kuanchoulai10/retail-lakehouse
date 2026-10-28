from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Engine

from adapter.outbound.managed_table.sql.managed_tables_sql_repo import (
    ManagedTablesSqlRepo,
)
from application.domain.model.discovery_rule.discovery_rule_id import DiscoveryRuleId
from application.exceptions import ConflictError
from application.domain.model.maintenance.maintenance_operation import (
    MaintenanceOperation,
)
from application.domain.model.maintenance_settings.maintenance_settings import (
    MaintenanceSettings,
)
from application.domain.model.managed_table.managed_table import ManagedTable
from application.domain.model.managed_table.operation_state import OperationState
from application.domain.model.managed_table.table_name import TableName
from application.domain.model.managed_table.table_selection import TableSelection
from application.domain.model.managed_table.table_status import TableStatus
from application.domain.model.managed_table.table_uuid import TableUuid
from application.domain.model.table_maintenance_preset.table_maintenance_preset_id import (
    TableMaintenancePresetId,
)

NOW = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)


def _table(
    uuid: str = "u1",
    name: TableName | None = None,
    status: TableStatus = TableStatus.ACTIVE,
    updated_at: datetime = NOW,
) -> ManagedTable:
    return ManagedTable(
        id=TableUuid(uuid),
        name=name or TableName("iceberg", "inventory", "orders"),
        status=status,
        selection=TableSelection.AUTO,
        settings=MaintenanceSettings(reconcile_interval=timedelta(minutes=45)),
        matched_rule_id=DiscoveryRuleId("r1"),
        source_preset_id=TableMaintenancePresetId("t1"),
        registered_at=NOW,
        updated_at=updated_at,
        operation_states={
            MaintenanceOperation.REWRITE_DATA_FILES: OperationState(
                last_attempt_at=NOW, consecutive_failures=2
            ),
            MaintenanceOperation.EXPIRE_SNAPSHOTS: OperationState(),
        },
    )


@pytest.fixture
def repo(engine: Engine) -> ManagedTablesSqlRepo:
    return ManagedTablesSqlRepo(engine)


def test_roundtrip_field_by_field(repo: ManagedTablesSqlRepo):
    original = _table()
    repo.create(original)
    loaded = repo.get(TableUuid("u1"))
    assert loaded is not None
    assert loaded.id == original.id
    assert loaded.name == original.name
    assert loaded.status is TableStatus.ACTIVE
    assert loaded.selection is TableSelection.AUTO
    assert loaded.settings == original.settings
    assert loaded.matched_rule_id == DiscoveryRuleId("r1")
    assert loaded.source_preset_id == TableMaintenancePresetId("t1")
    assert loaded.registered_at == NOW
    assert loaded.registered_at.tzinfo is not None
    assert loaded.updated_at == NOW
    assert loaded.operation_states == original.operation_states
    state = loaded.operation_states[MaintenanceOperation.REWRITE_DATA_FILES]
    assert state.last_attempt_at == NOW
    assert state.last_attempt_at is not None
    assert state.last_attempt_at.tzinfo is not None
    assert loaded.collect_events() == []


def test_roundtrip_with_none_settings_and_links(repo: ManagedTablesSqlRepo):
    table = _table()
    table.settings = None
    table.matched_rule_id = None
    table.source_preset_id = None
    table.operation_states = {}
    repo.create(table)
    loaded = repo.get(table.id)
    assert loaded is not None
    assert loaded.settings is None
    assert loaded.matched_rule_id is None
    assert loaded.source_preset_id is None
    assert loaded.operation_states == {}


def test_loaded_state_does_not_alias_between_loads(repo: ManagedTablesSqlRepo):
    repo.create(_table())
    first = repo.get(TableUuid("u1"))
    second = repo.get(TableUuid("u1"))
    assert first is not None
    assert second is not None
    first.operation_states.clear()
    assert second.operation_states


def test_get_missing_returns_none(repo: ManagedTablesSqlRepo):
    assert repo.get(TableUuid("nope")) is None


def test_update_persists_changes(repo: ManagedTablesSqlRepo):
    table = _table()
    repo.create(table)
    later = NOW + timedelta(hours=1)
    table.status = TableStatus.PAUSED
    table.updated_at = later
    table.operation_states[MaintenanceOperation.REWRITE_MANIFESTS] = OperationState(
        last_attempt_at=later, consecutive_failures=1
    )
    repo.update(table)
    loaded = repo.get(table.id)
    assert loaded is not None
    assert loaded.status is TableStatus.PAUSED
    assert loaded.updated_at == later
    assert loaded.operation_states == table.operation_states


def test_update_missing_raises(repo: ManagedTablesSqlRepo):
    with pytest.raises(LookupError):
        repo.update(_table("ghost"))


def test_find_by_name_exact_match(repo: ManagedTablesSqlRepo):
    repo.create(_table("u1", TableName("iceberg", "inventory", "orders")))
    repo.create(_table("u2", TableName("iceberg", "inventory", "orders2")))
    found = repo.find_by_name(TableName("iceberg", "inventory", "orders"))
    assert found is not None
    assert found.id == TableUuid("u1")
    assert repo.find_by_name(TableName("iceberg", "inventory", "Orders")) is None
    assert repo.find_by_name(TableName("other", "inventory", "orders")) is None


def test_find_by_name_ignores_dropped_and_allows_reuse(repo: ManagedTablesSqlRepo):
    name = TableName("iceberg", "inventory", "orders")
    repo.create(_table("old", name, TableStatus.DROPPED))
    assert repo.find_by_name(name) is None
    repo.create(_table("new", name, TableStatus.ACTIVE))
    found = repo.find_by_name(name)
    assert found is not None
    assert found.id == TableUuid("new")


def test_find_by_name_prefers_most_recently_updated(repo: ManagedTablesSqlRepo):
    name = TableName("iceberg", "inventory", "orders")
    repo.create(_table("a", name, updated_at=NOW))
    repo.create(_table("b", name, updated_at=NOW + timedelta(minutes=1)))
    found = repo.find_by_name(name)
    assert found is not None
    assert found.id == TableUuid("b")


def test_list_by_statuses(repo: ManagedTablesSqlRepo):
    repo.create(_table("a", TableName("c", "n", "a"), TableStatus.ACTIVE))
    repo.create(_table("b", TableName("c", "n", "b"), TableStatus.PAUSED))
    repo.create(_table("c", TableName("c", "n", "c"), TableStatus.DROPPED))
    got = repo.list_by_statuses([TableStatus.ACTIVE, TableStatus.PAUSED])
    assert [t.id.value for t in got] == ["a", "b"]
    assert repo.list_by_statuses([]) == []


def test_list_all_ordered_by_name(repo: ManagedTablesSqlRepo):
    repo.create(_table("1", TableName("b", "n", "t")))
    repo.create(_table("2", TableName("a", "z", "t")))
    repo.create(_table("3", TableName("a", "n", "z")))
    repo.create(_table("4", TableName("a", "n", "a")))
    assert [t.id.value for t in repo.list_all()] == ["4", "3", "2", "1"]


def test_create_duplicate_primary_key_raises_conflict(repo: ManagedTablesSqlRepo):
    repo.create(_table("dup"))
    with pytest.raises(ConflictError):
        repo.create(_table("dup", TableName("c", "n", "other")))
