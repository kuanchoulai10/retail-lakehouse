"""Test the table use case services."""

from __future__ import annotations

import pytest

from context.table_maintenance.application.domain.model.shared import MaintenanceOperation
from context.table_maintenance.application.domain.model.table import (
    Table,
    TableId,
    TableName,
)
from context.table_maintenance.application.domain.model.table_discovery_rules import (
    TableDiscoveryRuleId,
)
from context.table_maintenance.application.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from context.table_maintenance.application.port.inbound.table import (
    GetTableUseCaseInput,
    ListTablesUseCaseInput,
    TriggerTableMaintenanceUseCaseInput,
    TriggerTableReconciliationUseCaseInput,
)
from context.table_maintenance.application.service.table import (
    GetTableService,
    ListTablesService,
    TriggerTableMaintenanceService,
    TriggerTableReconciliationService,
)

NAME = TableName(catalog="iceberg", namespace="sales", table="orders")


def _managed(repo, now, uuid="u-1", name=NAME):
    table = Table.register(TableId(uuid), name, TableDiscoveryRuleId("r-1"), now)
    repo.create(table)
    return table


def _unmanaged(repo, now, uuid="u-1", name=NAME):
    table = _managed(repo, now, uuid, name)
    table.unmanage(now)
    return table


def _dropped(repo, now, uuid="u-1", name=NAME):
    table = _managed(repo, now, uuid, name)
    table.mark_dropped(now)
    return table


def _change(call):
    return (call.table_uuid, call.change, call.operations, call.is_managed)


# --- list / get ---


def test_list_tables_all_and_by_status(tables_repo, now):
    """Listing returns all tables, or only those of the requested status."""
    _managed(tables_repo, now, "u-1")
    _unmanaged(tables_repo, now, "u-2", TableName(catalog="iceberg", namespace="sales", table="items"))
    service = ListTablesService(tables_repo)
    assert len(service.execute(ListTablesUseCaseInput()).items) == 2
    out = service.execute(ListTablesUseCaseInput(status="unmanaged"))
    assert [i.uuid for i in out.items] == ["u-2"]
    assert out.items[0].status == "unmanaged"


def test_list_tables_unknown_status_is_invalid(tables_repo):
    """Listing with an unknown status raises a ValidationError; the old statuses are unknown."""
    for status in ("sleeping", "active", "paused", "excluded"):
        with pytest.raises(ValidationError):
            ListTablesService(tables_repo).execute(ListTablesUseCaseInput(status=status))


def test_get_table_includes_status_rule_and_operation_states(tables_repo, now):
    """Getting a table returns its name, status, deciding rule and operation states."""
    table = _managed(tables_repo, now)
    table.record_operation_result(MaintenanceOperation.EXPIRE_SNAPSHOTS, False, now)
    out = GetTableService(tables_repo).execute(GetTableUseCaseInput(uuid="u-1"))
    assert (out.catalog, out.namespace, out.table) == ("iceberg", "sales", "orders")
    assert out.status == "managed"
    assert out.matched_rule_id == "r-1"
    assert out.operation_states["expire_snapshots"] == {
        "last_attempt_at": now,
        "consecutive_failures": 1,
    }


def test_get_unknown_table_not_found(tables_repo):
    """Getting an unknown table raises NotFoundError."""
    with pytest.raises(NotFoundError):
        GetTableService(tables_repo).execute(GetTableUseCaseInput(uuid="nope"))


# --- trigger ---


def test_trigger_signals_operations_in_canonical_order(tables_repo, signals, now):
    """Triggering signals the requested operations in canonical order."""
    _managed(tables_repo, now)
    out = TriggerTableMaintenanceService(tables_repo, signals).execute(
        TriggerTableMaintenanceUseCaseInput(
            uuid="u-1",
            operations=["expire_snapshots", "rewrite_data_files", "expire_snapshots"],
        )
    )
    assert out.accepted is True
    assert [_change(c) for c in signals.calls] == [
        (
            "u-1",
            "maintenance_requested",
            ["rewrite_data_files", "expire_snapshots"],
            True,
        )
    ]


def test_trigger_on_dropped_table_conflicts(tables_repo, signals, now):
    """Triggering maintenance on a dropped table raises ConflictError."""
    _dropped(tables_repo, now)
    with pytest.raises(ConflictError):
        TriggerTableMaintenanceService(tables_repo, signals).execute(
            TriggerTableMaintenanceUseCaseInput(uuid="u-1", operations=["rewrite_data_files"])
        )
    assert signals.calls == []


def test_trigger_on_unmanaged_table_conflicts(tables_repo, signals, now):
    """Triggering maintenance on an unmanaged table raises ConflictError."""
    _unmanaged(tables_repo, now)
    with pytest.raises(ConflictError):
        TriggerTableMaintenanceService(tables_repo, signals).execute(
            TriggerTableMaintenanceUseCaseInput(uuid="u-1", operations=["rewrite_data_files"])
        )


@pytest.mark.parametrize("operations", [[], ["defrag"]])
def test_trigger_invalid_operations(tables_repo, signals, now, operations):
    """Invalid operations are rejected and nothing is signalled."""
    _managed(tables_repo, now)
    with pytest.raises(ValidationError):
        TriggerTableMaintenanceService(tables_repo, signals).execute(
            TriggerTableMaintenanceUseCaseInput(uuid="u-1", operations=operations)
        )
    assert signals.calls == []


def test_trigger_unknown_table(tables_repo, signals):
    """Triggering maintenance on an unknown table raises NotFoundError."""
    with pytest.raises(NotFoundError):
        TriggerTableMaintenanceService(tables_repo, signals).execute(
            TriggerTableMaintenanceUseCaseInput(uuid="nope", operations=["rewrite_data_files"])
        )


# --- reconcile now ---


def test_reconcile_now_signals_the_workflow(tables_repo, signals, now):
    """Reconciling now sends a reconcile request to the table's workflow."""
    _managed(tables_repo, now)
    out = TriggerTableReconciliationService(tables_repo, signals).execute(
        TriggerTableReconciliationUseCaseInput(uuid="u-1")
    )
    assert out.accepted is True
    assert [_change(c) for c in signals.calls] == [("u-1", "reconcile_requested", [], True)]


@pytest.mark.parametrize("make", [_unmanaged, _dropped], ids=["unmanaged", "dropped"])
def test_reconcile_now_on_table_out_of_maintenance_conflicts(tables_repo, signals, now, make):
    """Reconciling a table that is not managed raises ConflictError and signals nothing."""
    make(tables_repo, now)
    with pytest.raises(ConflictError):
        TriggerTableReconciliationService(tables_repo, signals).execute(
            TriggerTableReconciliationUseCaseInput(uuid="u-1")
        )
    assert signals.calls == []


def test_reconcile_now_unknown_table(tables_repo, signals):
    """Reconciling an unknown table raises NotFoundError."""
    with pytest.raises(NotFoundError):
        TriggerTableReconciliationService(tables_repo, signals).execute(
            TriggerTableReconciliationUseCaseInput(uuid="nope")
        )
    assert signals.calls == []
