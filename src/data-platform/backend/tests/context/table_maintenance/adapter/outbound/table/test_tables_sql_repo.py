"""Test the SQL repository of the Table aggregate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from context.table_maintenance.adapter.outbound.table.sql import TablesSqlRepo
from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
    MaintenanceSettings,
)
from context.table_maintenance.application.domain.model.table import (
    OperationState,
    Table,
    TableId,
    TableName,
    TableSelection,
    TableStatus,
)
from context.table_maintenance.application.domain.model.table_discovery_rule import (
    TableDiscoveryRuleId,
)
from context.table_maintenance.application.domain.model.table_maintenance_preset import (
    TableMaintenancePresetId,
)
from context.table_maintenance.application.exceptions import ConflictError

if TYPE_CHECKING:
    from sqlalchemy import Engine

NOW = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)


def _table(
    uuid: str = "u1",
    name: TableName | None = None,
    status: TableStatus = TableStatus.ACTIVE,
    updated_at: datetime = NOW,
) -> Table:
    return Table(
        id=TableId(uuid),
        name=name or TableName(catalog="iceberg", namespace="inventory", table="orders"),
        status=status,
        selection=TableSelection.AUTO,
        settings=MaintenanceSettings(reconcile_interval=timedelta(minutes=45)),
        matched_rule_id=TableDiscoveryRuleId("r1"),
        source_preset_id=TableMaintenancePresetId("t1"),
        registered_at=NOW,
        updated_at=updated_at,
        operation_states={
            MaintenanceOperation.REWRITE_DATA_FILES: OperationState(last_attempt_at=NOW, consecutive_failures=2),
            MaintenanceOperation.EXPIRE_SNAPSHOTS: OperationState(),
        },
    )


@pytest.fixture
def repo(engine: Engine) -> TablesSqlRepo:
    """Provide the tables repository on the test engine."""
    return TablesSqlRepo(engine)


def test_roundtrip_field_by_field(repo: TablesSqlRepo):
    """A stored table loads back with every field equal."""
    original = _table()
    repo.create(original)
    loaded = repo.get(TableId("u1"))
    assert loaded is not None
    assert loaded.id == original.id
    assert loaded.name == original.name
    assert loaded.status is TableStatus.ACTIVE
    assert loaded.selection is TableSelection.AUTO
    assert loaded.settings == original.settings
    assert loaded.matched_rule_id == TableDiscoveryRuleId("r1")
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


def test_roundtrip_reads_an_equal_aggregate(repo: TablesSqlRepo):
    """A stored row reads back into a table whose every field, by value and type, is the original's."""
    original = _table()
    repo.create(original)
    loaded = repo.get(TableId("u1"))
    assert loaded is not None
    assert loaded.model_dump() == original.model_dump()
    assert {name: type(getattr(loaded, name)) for name in Table.model_fields} == {
        name: type(getattr(original, name)) for name in Table.model_fields
    }


def test_roundtrip_with_none_settings_and_links(repo: TablesSqlRepo):
    """A table without settings or rule and preset links round trips with them as None."""
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


def test_loaded_state_does_not_alias_between_loads(repo: TablesSqlRepo):
    """Two loads of a table do not share mutable state."""
    repo.create(_table())
    first = repo.get(TableId("u1"))
    second = repo.get(TableId("u1"))
    assert first is not None
    assert second is not None
    first.operation_states.clear()
    assert second.operation_states


def test_get_missing_returns_none(repo: TablesSqlRepo):
    """Getting a table that does not exist returns None."""
    assert repo.get(TableId("nope")) is None


def test_update_persists_changes(repo: TablesSqlRepo):
    """An update persists the new status and update time."""
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


def test_update_missing_raises(repo: TablesSqlRepo):
    """Updating a table that does not exist raises LookupError."""
    with pytest.raises(LookupError):
        repo.update(_table("ghost"))


def test_find_by_name_exact_match(repo: TablesSqlRepo):
    """Finding by name matches the exact catalog, namespace and table name."""
    repo.create(_table("u1", TableName(catalog="iceberg", namespace="inventory", table="orders")))
    repo.create(_table("u2", TableName(catalog="iceberg", namespace="inventory", table="orders2")))
    found = repo.find_by_name(TableName(catalog="iceberg", namespace="inventory", table="orders"))
    assert found is not None
    assert found.id == TableId("u1")
    assert repo.find_by_name(TableName(catalog="iceberg", namespace="inventory", table="Orders")) is None
    assert repo.find_by_name(TableName(catalog="other", namespace="inventory", table="orders")) is None


def test_find_by_name_ignores_dropped_and_allows_reuse(repo: TablesSqlRepo):
    """Finding by name ignores dropped tables, so a name can be reused by a new table."""
    name = TableName(catalog="iceberg", namespace="inventory", table="orders")
    repo.create(_table("old", name, TableStatus.DROPPED))
    assert repo.find_by_name(name) is None
    repo.create(_table("new", name, TableStatus.ACTIVE))
    found = repo.find_by_name(name)
    assert found is not None
    assert found.id == TableId("new")


def test_find_by_name_prefers_most_recently_updated(repo: TablesSqlRepo):
    """When several tables share a name the most recently updated one is found."""
    name = TableName(catalog="iceberg", namespace="inventory", table="orders")
    repo.create(_table("a", name, updated_at=NOW))
    repo.create(_table("b", name, updated_at=NOW + timedelta(minutes=1)))
    found = repo.find_by_name(name)
    assert found is not None
    assert found.id == TableId("b")


def test_list_by_statuses(repo: TablesSqlRepo):
    """Listing by statuses returns the tables in those statuses and none for an empty list."""
    repo.create(_table("a", TableName(catalog="c", namespace="n", table="a"), TableStatus.ACTIVE))
    repo.create(_table("b", TableName(catalog="c", namespace="n", table="b"), TableStatus.PAUSED))
    repo.create(_table("c", TableName(catalog="c", namespace="n", table="c"), TableStatus.DROPPED))
    got = repo.list_by_statuses([TableStatus.ACTIVE, TableStatus.PAUSED])
    assert [t.id.value for t in got] == ["a", "b"]
    assert repo.list_by_statuses([]) == []


def test_list_all_ordered_by_name(repo: TablesSqlRepo):
    """Listing all tables orders them by name."""
    repo.create(_table("1", TableName(catalog="b", namespace="n", table="t")))
    repo.create(_table("2", TableName(catalog="a", namespace="z", table="t")))
    repo.create(_table("3", TableName(catalog="a", namespace="n", table="z")))
    repo.create(_table("4", TableName(catalog="a", namespace="n", table="a")))
    assert [t.id.value for t in repo.list_all()] == ["4", "3", "2", "1"]


def test_create_duplicate_primary_key_raises_conflict(repo: TablesSqlRepo):
    """Creating a table with an existing id raises ConflictError."""
    repo.create(_table("dup"))
    with pytest.raises(ConflictError):
        repo.create(_table("dup", TableName(catalog="c", namespace="n", table="other")))


def test_tables_sql_table_name_is_tables():
    """The tables SQL table is named tables."""
    from context.table_maintenance.adapter.outbound.table.sql import tables_table

    assert tables_table.name == "tables"
