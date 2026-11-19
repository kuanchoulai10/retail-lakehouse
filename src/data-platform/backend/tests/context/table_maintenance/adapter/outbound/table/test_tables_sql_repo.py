"""Test the SQL repository of the Table aggregate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine, inspect, text

from context.table_maintenance.adapter.outbound.shared.sql import create_schema
from context.table_maintenance.adapter.outbound.table.sql import TablesSqlRepo, tables_table
from context.table_maintenance.application.domain.model.shared import (
    ComputeSize,
    MaintenanceOperation,
)
from context.table_maintenance.application.domain.model.table import (
    AppliedPolicyRef,
    AttentionMark,
    OperationState,
    RecordedAttempt,
    Table,
    TableId,
    TableName,
    TableStatus,
)
from context.table_maintenance.application.domain.model.table_discovery_rules import (
    TableDiscoveryRuleId,
    TableDiscoveryRules,
)
from context.table_maintenance.application.exceptions import ConflictError
from context.table_maintenance.application.service.table import apply_discovery_to_known_table
from tests.context.table_maintenance.fakes.in_memory_tables_repo import InMemoryTablesRepo
from tests.context.table_maintenance.fakes.recording_send_table_change_gateway import (
    RecordingSendTableChangeGateway,
)

if TYPE_CHECKING:
    from pathlib import Path

    from sqlalchemy import Engine

    from context.table_maintenance.application.port.outbound.table import TablesRepo

RULE_1 = "dr-00000000000000000000000001"
NOW = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)


def _table(
    uuid: str = "u1",
    name: TableName | None = None,
    status: TableStatus = TableStatus.MANAGED,
    updated_at: datetime = NOW,
) -> Table:
    return Table(
        id=TableId(uuid),
        name=name or TableName(catalog="iceberg", namespace="inventory", table="orders"),
        status=status,
        matched_rule_id=TableDiscoveryRuleId(RULE_1),
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
    assert loaded.status is TableStatus.MANAGED
    assert loaded.matched_rule_id == TableDiscoveryRuleId(RULE_1)
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


def test_roundtrip_of_an_unmanaged_table_without_a_rule(repo: TablesSqlRepo):
    """An unmanaged table without a deciding rule round trips with its status and no rule."""
    table = _table(status=TableStatus.UNMANAGED)
    table.matched_rule_id = None
    table.operation_states = {}
    repo.create(table)
    loaded = repo.get(table.id)
    assert loaded is not None
    assert loaded.status is TableStatus.UNMANAGED
    assert loaded.matched_rule_id is None
    assert loaded.operation_states == {}


def test_tables_have_no_selection_settings_or_preset_columns(engine: Engine):
    """The tables table keeps no manual selection, per-table settings or source preset."""
    columns = {c["name"] for c in inspect(engine).get_columns("tables")}
    assert not {"selection", "settings_json", "source_preset_id"} & columns


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
    table.status = TableStatus.UNMANAGED
    table.updated_at = later
    table.operation_states[MaintenanceOperation.REWRITE_MANIFESTS] = OperationState(
        last_attempt_at=later, consecutive_failures=1
    )
    repo.update(table)
    loaded = repo.get(table.id)
    assert loaded is not None
    assert loaded.status is TableStatus.UNMANAGED
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
    repo.create(_table("new", name, TableStatus.MANAGED))
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
    repo.create(_table("a", TableName(catalog="c", namespace="n", table="a"), TableStatus.MANAGED))
    repo.create(_table("b", TableName(catalog="c", namespace="n", table="b"), TableStatus.UNMANAGED))
    repo.create(_table("c", TableName(catalog="c", namespace="n", table="c"), TableStatus.DROPPED))
    got = repo.list_by_statuses([TableStatus.MANAGED, TableStatus.UNMANAGED])
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


def test_operation_state_round_trips_size_and_attention(repo: TablesSqlRepo):
    """The remembered size and a needs-attention mark load back unchanged."""
    table = _table()
    mark = AttentionMark(
        since=NOW,
        reason="out of memory at size L",
        policy=AppliedPolicyRef(
            name="nightly", version=3, target={"type": "table", "path": ["iceberg", "inventory"], "table_uuid": "u1"}
        ),
    )
    table.operation_states = {
        MaintenanceOperation.REWRITE_DATA_FILES: OperationState(
            last_attempt_at=NOW,
            last_successful_size=ComputeSize.L,
            attention=mark,
            last_recorded=RecordedAttempt(run_id="run-7", attempt=3),
        ),
        MaintenanceOperation.EXPIRE_SNAPSHOTS: OperationState(last_successful_size=ComputeSize.M, low_use_successes=2),
    }
    repo.create(table)
    loaded = repo.get(TableId("u1"))
    assert loaded is not None
    assert loaded.operation_states == table.operation_states


def test_operation_state_without_new_keys_decodes_with_defaults(repo: TablesSqlRepo, engine: Engine):
    """A row written before sizes and attention existed decodes with no size and no mark."""
    repo.create(_table())
    with engine.begin() as conn:
        conn.execute(
            tables_table.update().values(
                operation_states_json={
                    "rewrite_data_files": {"last_attempt_at": NOW.isoformat(), "consecutive_failures": 1}
                }
            )
        )
    loaded = repo.get(TableId("u1"))
    assert loaded is not None
    state = loaded.operation_state(MaintenanceOperation.REWRITE_DATA_FILES)
    assert state == OperationState(last_attempt_at=NOW, consecutive_failures=1)
    assert state.start_size() is ComputeSize.S
    assert state.low_use_successes == 0


def test_last_commit_and_last_discovery_round_trip(repo: TablesSqlRepo):
    """A table's last commit and the last discovery stamped when it was dropped are stored and read back."""
    table = _table()
    table.record_last_commit(NOW + timedelta(minutes=5))
    table.mark_dropped(NOW + timedelta(minutes=20), catalog_discovered_at=NOW + timedelta(minutes=10))
    repo.create(table)
    loaded = repo.get(table.id)
    assert loaded is not None
    assert loaded.last_committed_at == NOW + timedelta(minutes=5)
    assert loaded.last_discovered_at == NOW + timedelta(minutes=10)
    assert loaded.last_committed_at is not None
    assert loaded.last_committed_at.tzinfo is not None


def test_a_table_stored_before_the_two_times_reads_them_as_unknown(tmp_path: Path):
    """A row stored by an older release gains the two columns, empty, and reads as unknown."""
    engine = create_engine(f"sqlite:///{tmp_path / 'tables.db'}")
    create_schema(engine)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE tables DROP COLUMN last_committed_at"))
        connection.execute(text("ALTER TABLE tables DROP COLUMN last_discovered_at"))
        connection.execute(
            text(
                "INSERT INTO tables (uuid, catalog, namespace, table_name, status, matched_rule_id,"
                " registered_at, updated_at, operation_states_json)"
                " VALUES ('u-old', 'iceberg', 'sales', 'orders', 'managed', NULL,"
                " '2026-10-24 12:00:00.000000', '2026-10-24 12:00:00.000000', '{}')"
            )
        )
    create_schema(engine)
    loaded = TablesSqlRepo(engine).get(TableId("u-old"))
    assert loaded is not None
    assert (loaded.last_committed_at, loaded.last_discovered_at) == (None, None)


@pytest.fixture(params=["sql", "memory"])
def either_repo(request: pytest.FixtureRequest, engine: Engine) -> TablesRepo:
    """Provide each tables repository implementation."""
    if request.param == "sql":
        return TablesSqlRepo(engine)
    return InMemoryTablesRepo()


def test_recording_a_newer_commit_moves_only_forward(either_repo: TablesRepo):
    """The narrow write sets a first commit, moves to a newer one and refuses an older or equal one."""
    either_repo.create(_table())
    later = NOW + timedelta(minutes=5)
    assert either_repo.record_last_commit(TableId("u1"), NOW) is True
    assert either_repo.record_last_commit(TableId("u1"), later) is True
    assert either_repo.record_last_commit(TableId("u1"), NOW) is False
    assert either_repo.record_last_commit(TableId("u1"), later) is False
    loaded = either_repo.get(TableId("u1"))
    assert loaded is not None
    assert loaded.last_committed_at == later


def test_recording_a_commit_of_a_dropped_or_unknown_table_changes_nothing(either_repo: TablesRepo):
    """A dropped table keeps its last commit, as the aggregate refuses it, and an unknown table is no write."""
    either_repo.create(_table(status=TableStatus.DROPPED))
    assert either_repo.record_last_commit(TableId("u1"), NOW) is False
    assert either_repo.record_last_commit(TableId("nope"), NOW) is False
    loaded = either_repo.get(TableId("u1"))
    assert loaded is not None
    assert loaded.last_committed_at is None


def test_recording_a_commit_writes_nothing_else(repo: TablesSqlRepo):
    """A commit recorded from an older read leaves the operation result recorded since in place."""
    repo.create(_table())
    stale = repo.get(TableId("u1"))
    fresh = repo.get(TableId("u1"))
    assert stale is not None
    assert fresh is not None
    fresh.record_operation_result(MaintenanceOperation.REWRITE_DATA_FILES, True, NOW, size=ComputeSize.M)
    repo.update(fresh)

    stale.record_last_commit(NOW + timedelta(minutes=5))
    repo.record_last_commit(stale.id, NOW + timedelta(minutes=5))

    loaded = repo.get(TableId("u1"))
    assert loaded is not None
    assert loaded.operation_states == fresh.operation_states
    assert loaded.last_committed_at == NOW + timedelta(minutes=5)


def test_a_commit_only_discovery_from_an_older_read_keeps_the_operation_result(repo: TablesSqlRepo):
    """Discovery seeing only a newer commit, on a copy read before a result was recorded, keeps that result."""
    unmanaged = _table(status=TableStatus.UNMANAGED)
    unmanaged.matched_rule_id = None
    repo.create(unmanaged)
    stale = repo.get(TableId("u1"))
    fresh = repo.get(TableId("u1"))
    assert stale is not None
    assert fresh is not None
    fresh.record_operation_result(MaintenanceOperation.REWRITE_DATA_FILES, False, NOW)
    repo.update(fresh)
    rules = TableDiscoveryRules.empty()

    apply_discovery_to_known_table(
        stale,
        stale.name,
        rules,
        repo,
        RecordingSendTableChangeGateway(),
        None,
        NOW,
        last_committed_at=NOW + timedelta(minutes=5),
    )

    loaded = repo.get(TableId("u1"))
    assert loaded is not None
    assert loaded.operation_states == fresh.operation_states
    assert loaded.last_committed_at == NOW + timedelta(minutes=5)


def test_a_full_update_from_an_older_copy_never_moves_the_last_commit_back(repo: TablesSqlRepo):
    """A full update carrying an older, or no, last commit keeps the newer one stored."""
    repo.create(_table())
    stale = repo.get(TableId("u1"))
    assert stale is not None
    stale.record_last_commit(NOW)
    repo.record_last_commit(TableId("u1"), NOW + timedelta(minutes=5))

    repo.update(stale)
    loaded = repo.get(TableId("u1"))
    assert loaded is not None
    assert loaded.last_committed_at == NOW + timedelta(minutes=5)

    never_seen = repo.get(TableId("u1"))
    assert never_seen is not None
    never_seen.last_committed_at = None
    repo.update(never_seen)
    loaded = repo.get(TableId("u1"))
    assert loaded is not None
    assert loaded.last_committed_at == NOW + timedelta(minutes=5)


def test_a_full_update_with_a_newer_last_commit_moves_it(repo: TablesSqlRepo):
    """A full update carrying a newer last commit stores it."""
    repo.create(_table())
    table = repo.get(TableId("u1"))
    assert table is not None
    table.record_last_commit(NOW + timedelta(minutes=5))
    repo.update(table)
    loaded = repo.get(TableId("u1"))
    assert loaded is not None
    assert loaded.last_committed_at == NOW + timedelta(minutes=5)
