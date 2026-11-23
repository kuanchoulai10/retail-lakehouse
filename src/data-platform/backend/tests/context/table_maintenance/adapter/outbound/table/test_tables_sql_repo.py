"""Test the SQL repository of the Table aggregate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import inspect

from context.table_maintenance.adapter.outbound.table.sql import TablesSqlRepo, tables_table
from context.table_maintenance.application.domain.model.shared import (
    ComputeSize,
    MaintenanceOperation,
    OverTargetPartition,
    PolicyTarget,
    PolicyTargetType,
    TableDiscoveryPolicyId,
    TableDiscoveryRuleId,
    TableId,
    TableMaintenancePolicyId,
    TableMaintenanceRunId,
    TablePriority,
)
from context.table_maintenance.application.domain.model.table import (
    AppliedPolicyRef,
    AttentionMark,
    OperationState,
    RecordedAttempt,
    Table,
    TableName,
    TableStatus,
)
from context.table_maintenance.application.domain.model.table_discovery_policy import (
    DiscoveryDecision,
    DiscoveryMatch,
    DiscoveryOutcome,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy import TableMaintenancePolicyName
from context.table_maintenance.application.exceptions import ConflictError
from context.table_maintenance.application.service.table import apply_discovery_to_known_table
from tests.context.table_maintenance.fakes.in_memory_tables_repo import InMemoryTablesRepo
from tests.context.table_maintenance.fakes.recording_send_table_change_gateway import (
    RecordingSendTableChangeGateway,
)

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from context.table_maintenance.application.port.outbound.table import TablesRepo
RUN_7 = "mr-00000000000000000000000007"

RULE_1 = "dr-00000000000000000000000001"
NIGHTLY = TableMaintenancePolicyId("mp-00000000000000000000000003")
NOW = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)
SALES_POLICY = TableDiscoveryPolicyId("dp-00000000000000000000000004")
MATCH = DiscoveryMatch(policy_id=SALES_POLICY, policy_version=3, rule_id=TableDiscoveryRuleId(RULE_1))
NO_RULE_MATCH = DiscoveryMatch(policy_id=SALES_POLICY, policy_version=3, rule_id=None)


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
        discovered_by=MATCH,
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
    assert loaded.discovered_by == MATCH
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
    """An unmanaged table its policy's no-match outcome decided round trips with its status, policy and no rule."""
    table = _table(status=TableStatus.UNMANAGED)
    table.discovered_by = NO_RULE_MATCH
    table.operation_states = {}
    repo.create(table)
    loaded = repo.get(table.id)
    assert loaded is not None
    assert loaded.status is TableStatus.UNMANAGED
    assert loaded.discovered_by == NO_RULE_MATCH
    assert loaded.operation_states == {}


def test_the_deciding_policy_and_version_are_stored_in_their_columns(repo: TablesSqlRepo, engine: Engine):
    """The policy id and version that decided a table are columns of its row, beside its rule."""
    repo.create(_table())
    with engine.connect() as connection:
        row = connection.execute(tables_table.select()).mappings().one()
    assert (row["matched_policy_id"], row["matched_policy_version"], row["matched_rule_id"]) == (
        SALES_POLICY.value,
        3,
        RULE_1,
    )


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
    first.operation_states = {}
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
    table.operation_states = {
        **table.operation_states,
        MaintenanceOperation.REWRITE_MANIFESTS: OperationState(last_attempt_at=later, consecutive_failures=1),
    }
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
            policy_id=NIGHTLY,
            version=3,
            target=PolicyTarget(type=PolicyTargetType.TABLE, path=("iceberg", "inventory"), table_uuid="u1"),
        ),
        policy_name=TableMaintenancePolicyName(value="nightly"),
    )
    table.operation_states = {
        MaintenanceOperation.REWRITE_DATA_FILES: OperationState(
            last_attempt_at=NOW,
            last_successful_size=ComputeSize.L,
            attention=mark,
            last_recorded=RecordedAttempt(run_id=TableMaintenanceRunId(RUN_7), attempt=3),
        ),
        MaintenanceOperation.EXPIRE_SNAPSHOTS: OperationState(last_successful_size=ComputeSize.M, low_use_successes=2),
    }
    repo.create(table)
    loaded = repo.get(TableId("u1"))
    assert loaded is not None
    assert loaded.operation_states == table.operation_states


def test_attention_mark_is_stored_with_the_policy_id(repo: TablesSqlRepo, engine: Engine):
    """A needs-attention mark is stored as ``{"policy": {"id", "version", "target", "name"}}``, by the policy id."""
    table = _table()
    mark = AttentionMark(
        since=NOW,
        reason="r",
        policy=AppliedPolicyRef(policy_id=NIGHTLY, version=3, target=None),
        policy_name=TableMaintenancePolicyName(value="nightly"),
    )
    table.operation_states = {MaintenanceOperation.REWRITE_DATA_FILES: OperationState(attention=mark)}
    repo.create(table)

    with engine.connect() as conn:
        stored = conn.execute(tables_table.select()).one()._mapping["operation_states_json"]

    assert stored["rewrite_data_files"]["attention"]["policy"] == {
        "id": NIGHTLY.value,
        "version": 3,
        "target": None,
        "name": "nightly",
    }


def test_attention_mark_stores_its_target_and_reads_it_back(repo: TablesSqlRepo, engine: Engine):
    """A mark's target is stored in its wire form and reads back as the same target."""
    table = _table()
    target = PolicyTarget(type=PolicyTargetType.NAMESPACE, path=("iceberg", "e2e"))
    mark = AttentionMark(
        since=NOW,
        reason="r",
        policy=AppliedPolicyRef(policy_id=NIGHTLY, version=3, target=target),
        policy_name=TableMaintenancePolicyName(value="nightly"),
    )
    table.operation_states = {MaintenanceOperation.REWRITE_DATA_FILES: OperationState(attention=mark)}
    repo.create(table)

    with engine.connect() as conn:
        stored = conn.execute(tables_table.select()).one()._mapping["operation_states_json"]
    loaded = repo.get(TableId("u1"))

    assert stored["rewrite_data_files"]["attention"]["policy"]["target"] == {
        "type": "namespace",
        "path": ["iceberg", "e2e"],
        "table_uuid": None,
    }
    assert loaded is not None
    assert loaded.operation_state(MaintenanceOperation.REWRITE_DATA_FILES).attention == mark


def test_attention_mark_under_the_platform_default_reads_back_without_a_target(repo: TablesSqlRepo):
    """A mark set under the platform default (no target) reads back with no target."""
    table = _table()
    mark = AttentionMark(
        since=NOW,
        reason="r",
        policy=AppliedPolicyRef(policy_id=NIGHTLY, version=3),
        policy_name=TableMaintenancePolicyName(value="nightly"),
    )
    table.operation_states = {MaintenanceOperation.REWRITE_DATA_FILES: OperationState(attention=mark)}
    repo.create(table)
    loaded = repo.get(TableId("u1"))
    assert loaded is not None
    assert loaded.operation_state(MaintenanceOperation.REWRITE_DATA_FILES).attention == mark


def test_a_recorded_attempt_is_stored_as_its_run_id_string(repo: TablesSqlRepo, engine: Engine):
    """A recorded attempt is stored as ``{"run_id": "mr-…", "attempt": n}``, and a row of that shape reads back."""
    table = _table()
    attempt = RecordedAttempt(run_id=TableMaintenanceRunId(RUN_7), attempt=3)
    table.operation_states = {MaintenanceOperation.REWRITE_DATA_FILES: OperationState(last_recorded=attempt)}
    repo.create(table)

    with engine.connect() as conn:
        stored = conn.execute(tables_table.select()).one()._mapping["operation_states_json"]
    assert stored["rewrite_data_files"]["last_recorded"] == {"run_id": RUN_7, "attempt": 3}

    with engine.begin() as conn:
        conn.execute(
            tables_table.update().values(
                operation_states_json={
                    "rewrite_data_files": {
                        "last_attempt_at": None,
                        "consecutive_failures": 0,
                        "last_successful_size": None,
                        "attention": None,
                        "low_use_successes": 0,
                        "last_recorded": {"run_id": RUN_7, "attempt": 3},
                    }
                }
            )
        )
    loaded = repo.get(TableId("u1"))
    assert loaded is not None
    assert loaded.operation_state(MaintenanceOperation.REWRITE_DATA_FILES).last_recorded == attempt


def test_an_attention_mark_without_its_start_time_is_refused(repo: TablesSqlRepo, engine: Engine):
    """A stored mark with no start time is refused, naming the missing start time."""
    repo.create(_table())
    policy = {"id": NIGHTLY.value, "version": 3, "target": None, "name": "nightly"}
    with engine.begin() as conn:
        conn.execute(
            tables_table.update().values(
                operation_states_json={
                    "rewrite_data_files": {
                        "last_attempt_at": None,
                        "consecutive_failures": 0,
                        "last_successful_size": None,
                        "attention": {"since": None, "reason": "r", "policy": policy},
                        "low_use_successes": 0,
                        "last_recorded": None,
                    }
                }
            )
        )
    with pytest.raises(ValueError, match="^an attention mark needs its start time$"):
        repo.get(TableId("u1"))


def test_an_over_target_partition_without_its_start_time_is_refused(repo: TablesSqlRepo, engine: Engine):
    """A stored over-target partition with no start time is refused, naming the missing start time."""
    repo.create(_table())
    with engine.begin() as conn:
        conn.execute(
            tables_table.update().values(over_target_partitions_json=[{"spec_id": 0, "values": ["a"], "since": None}])
        )
    with pytest.raises(ValueError, match="^an over-target partition needs its start time$"):
        repo.get(TableId("u1"))


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


def test_priority_round_trips(repo: TablesSqlRepo):
    """A table's priority is stored and read back."""
    table = _table()
    table.set_priority(TablePriority.P1, NOW + timedelta(minutes=1))
    repo.create(table)
    loaded = repo.get(table.id)
    assert loaded is not None
    assert loaded.priority is TablePriority.P1


@pytest.fixture(params=["sql", "memory"])
def either_repo(request: pytest.FixtureRequest, engine: Engine) -> TablesRepo:
    """Provide each tables repository implementation."""
    if request.param == "sql":
        return TablesSqlRepo(engine)
    return InMemoryTablesRepo()


def test_list_catalogs_with_managed_tables(either_repo: TablesRepo):
    """Each catalog holding a managed table is listed once, sorted; unmanaged and dropped tables do not count."""
    for uuid, catalog, status in (
        ("a", "lake", TableStatus.MANAGED),
        ("b", "iceberg", TableStatus.MANAGED),
        ("c", "iceberg", TableStatus.MANAGED),
        ("d", "quiet", TableStatus.UNMANAGED),
        ("e", "gone", TableStatus.DROPPED),
    ):
        either_repo.create(_table(uuid, TableName(catalog=catalog, namespace="n", table=uuid), status))

    assert either_repo.list_catalogs_with_managed_tables() == ["iceberg", "lake"]


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
    unmanaged.discovered_by = NO_RULE_MATCH
    repo.create(unmanaged)
    stale = repo.get(TableId("u1"))
    fresh = repo.get(TableId("u1"))
    assert stale is not None
    assert fresh is not None
    fresh.record_operation_result(MaintenanceOperation.REWRITE_DATA_FILES, False, NOW)
    repo.update(fresh)
    decision = DiscoveryDecision(outcome=DiscoveryOutcome.UNMANAGE, match=NO_RULE_MATCH)

    apply_discovery_to_known_table(
        stale,
        stale.name,
        decision,
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


def test_sql_round_trip_of_over_target_partitions(repo: TablesSqlRepo):
    """An int, a float, a bool, a None and a string with a quote come back equal, with their since."""
    repo.create(_table())
    entries = (OverTargetPartition(spec_id=0, values=("o'neil", 19700, 1.5, True, None), since=NOW),)
    assert repo.record_over_target_partitions(TableId("u1"), entries) is True
    loaded = repo.get(TableId("u1"))
    assert loaded is not None
    assert loaded.over_target_partitions == entries


def test_recording_the_same_over_target_partitions_again_keeps_them(either_repo: TablesRepo):
    """The narrow write answers whether a row matched, so a repeat is True and leaves the record as stored."""
    either_repo.create(_table())
    entries = (OverTargetPartition(spec_id=0, values=("eu",), since=NOW),)
    assert either_repo.record_over_target_partitions(TableId("u1"), entries) is True
    assert either_repo.record_over_target_partitions(TableId("u1"), entries) is True
    loaded = either_repo.get(TableId("u1"))
    assert loaded is not None
    assert loaded.over_target_partitions == entries


def test_update_keeps_the_stored_over_target_partitions(either_repo: TablesRepo):
    """Saving a copy read before the record was written keeps the stored record (the copy is a real snapshot)."""
    either_repo.create(_table())
    first_read = either_repo.get(TableId("u1"))
    assert first_read is not None
    stale = first_read.model_copy(deep=True)
    entries = (OverTargetPartition(spec_id=0, values=("eu",), since=NOW),)
    either_repo.record_over_target_partitions(TableId("u1"), entries)
    assert stale.over_target_partitions == ()
    stale.rename(TableName(catalog="c", namespace="n", table="renamed"), NOW)
    either_repo.update(stale)
    loaded = either_repo.get(TableId("u1"))
    assert loaded is not None
    assert loaded.name.table == "renamed"
    assert loaded.over_target_partitions == entries


def test_sql_update_does_not_overwrite_a_newer_over_target_record(repo: TablesSqlRepo):
    """SQL-adapter guarantee: an older read saved after a record was written leaves that record in place."""
    repo.create(_table())
    stale = repo.get(TableId("u1"))
    assert stale is not None
    entries = (OverTargetPartition(spec_id=0, values=("eu",), since=NOW),)
    repo.record_over_target_partitions(TableId("u1"), entries)
    stale.record_over_target_partitions(
        (OverTargetPartition(spec_id=0, values=("us",), since=NOW + timedelta(minutes=5)),)
    )
    repo.update(stale)
    loaded = repo.get(TableId("u1"))
    assert loaded is not None
    assert loaded.over_target_partitions == entries


def test_a_new_table_has_no_over_target_partitions(repo: TablesSqlRepo):
    """A table created without a record reads as holding none."""
    repo.create(_table())
    loaded = repo.get(TableId("u1"))
    assert loaded is not None
    assert loaded.over_target_partitions == ()


def test_over_target_partitions_of_a_dropped_or_unknown_table_are_not_written(either_repo: TablesRepo):
    """A dropped table keeps no record and an unknown table is no row, so neither reports a write."""
    either_repo.create(_table(status=TableStatus.DROPPED))
    entries = (OverTargetPartition(spec_id=0, values=("eu",), since=NOW),)
    assert either_repo.record_over_target_partitions(TableId("u1"), entries) is False
    assert either_repo.record_over_target_partitions(TableId("nope"), entries) is False
    loaded = either_repo.get(TableId("u1"))
    assert loaded is not None
    assert loaded.over_target_partitions == ()
