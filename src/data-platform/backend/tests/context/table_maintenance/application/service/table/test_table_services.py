"""Test the table use case services."""

from __future__ import annotations

import pytest

from context.table_maintenance.application.domain.model.shared import ComputeSize, MaintenanceOperation
from context.table_maintenance.application.domain.model.table import (
    AppliedPolicyRef,
    AttentionMark,
    Table,
    TableId,
    TableName,
)
from context.table_maintenance.application.domain.model.table_discovery_rules import (
    TableDiscoveryRuleId,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    MaintenancePolicyContent,
    TableMaintenancePolicy,
    TableMaintenancePolicyId,
    TableMaintenancePolicyName,
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
from tests.context.table_maintenance.fakes.in_memory_catalog_discoveries_repo import (
    InMemoryCatalogDiscoveriesRepo,
)
from tests.context.table_maintenance.fakes.in_memory_table_maintenance_policies_repo import (
    InMemoryTableMaintenancePoliciesRepo,
)

RULE_1 = "dr-00000000000000000000000001"
NAME = TableName(catalog="iceberg", namespace="sales", table="orders")


def _managed(repo, now, uuid="u-1", name=NAME):
    table = Table.register(TableId(uuid), name, TableDiscoveryRuleId(RULE_1), now)
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
    service = ListTablesService(tables_repo, InMemoryCatalogDiscoveriesRepo(), InMemoryTableMaintenancePoliciesRepo())
    assert len(service.execute(ListTablesUseCaseInput()).items) == 2
    out = service.execute(ListTablesUseCaseInput(status="unmanaged"))
    assert [i.uuid for i in out.items] == ["u-2"]
    assert out.items[0].status == "unmanaged"


def test_list_tables_unknown_status_is_invalid(tables_repo):
    """Listing with an unknown status raises a ValidationError; the old statuses are unknown."""
    for status in ("sleeping", "active", "paused", "excluded"):
        with pytest.raises(ValidationError):
            ListTablesService(
                tables_repo, InMemoryCatalogDiscoveriesRepo(), InMemoryTableMaintenancePoliciesRepo()
            ).execute(ListTablesUseCaseInput(status=status))


def test_get_table_includes_status_rule_and_operation_states(tables_repo, now):
    """Getting a table returns its name, status, deciding rule and operation states."""
    table = _managed(tables_repo, now)
    table.record_operation_result(MaintenanceOperation.EXPIRE_SNAPSHOTS, False, now)
    out = GetTableService(
        tables_repo, InMemoryCatalogDiscoveriesRepo(), InMemoryTableMaintenancePoliciesRepo()
    ).execute(GetTableUseCaseInput(uuid="u-1"))
    assert (out.catalog, out.namespace, out.table) == ("iceberg", "sales", "orders")
    assert out.status == "managed"
    assert out.matched_rule_id == RULE_1
    assert out.operation_states["expire_snapshots"] == {
        "last_attempt_at": now,
        "consecutive_failures": 1,
        "last_successful_size": None,
        "needs_attention": None,
    }


def test_get_unknown_table_not_found(tables_repo):
    """Getting an unknown table raises NotFoundError."""
    with pytest.raises(NotFoundError):
        GetTableService(tables_repo, InMemoryCatalogDiscoveriesRepo(), InMemoryTableMaintenancePoliciesRepo()).execute(
            GetTableUseCaseInput(uuid="nope")
        )


# --- trigger ---


def test_trigger_signals_operations_in_canonical_order(tables_repo, signals, now):
    """Triggering signals the requested operations in canonical order."""
    _managed(tables_repo, now)
    out = TriggerTableMaintenanceService(tables_repo, signals).execute(
        TriggerTableMaintenanceUseCaseInput(
            uuid="u-1", operations=("expire_snapshots", "rewrite_data_files", "expire_snapshots")
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
            TriggerTableMaintenanceUseCaseInput(uuid="u-1", operations=("rewrite_data_files",))
        )
    assert signals.calls == []


def test_trigger_on_unmanaged_table_conflicts(tables_repo, signals, now):
    """Triggering maintenance on an unmanaged table raises ConflictError."""
    _unmanaged(tables_repo, now)
    with pytest.raises(ConflictError):
        TriggerTableMaintenanceService(tables_repo, signals).execute(
            TriggerTableMaintenanceUseCaseInput(uuid="u-1", operations=("rewrite_data_files",))
        )


@pytest.mark.parametrize("operations", [(), ("defrag",)])
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
            TriggerTableMaintenanceUseCaseInput(uuid="nope", operations=("rewrite_data_files",))
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


def _mark_under(table, policy_id, now, name="nightly") -> None:
    mark = AttentionMark(
        since=now,
        reason="out of memory at size L",
        policy=AppliedPolicyRef(policy_id=policy_id, version=2, target=None),
        policy_name=TableMaintenancePolicyName(value=name),
    )
    table.mark_needs_attention(MaintenanceOperation.REWRITE_DATA_FILES, mark, now)


def test_get_table_shows_the_remembered_size_and_needs_attention(tables_repo, now):
    """A table's operation state shows its remembered size and its mark, naming the policy by id and current name."""
    policies = InMemoryTableMaintenancePoliciesRepo()
    nightly = TableMaintenancePolicy.create(
        TableMaintenancePolicyName(value="nightly"), MaintenancePolicyContent.platform_default(), now
    )
    policies.create(nightly)
    table = _managed(tables_repo, now)
    table.record_operation_result(MaintenanceOperation.REWRITE_DATA_FILES, True, now, size=ComputeSize.M)
    _mark_under(table, nightly.id, now)
    out = GetTableService(tables_repo, InMemoryCatalogDiscoveriesRepo(), policies).execute(
        GetTableUseCaseInput(uuid="u-1")
    )
    state = out.operation_states["rewrite_data_files"]
    assert state["last_successful_size"] == "M"
    assert state["needs_attention"] == {
        "since": now,
        "reason": "out of memory at size L",
        "policy_id": nightly.id.value,
        "policy_name": "nightly",
        "policy_deleted": False,
        "policy_version": 2,
    }


def test_attention_mark_keeps_the_policy_name_after_the_policy_is_deleted(tables_repo, now):
    """A mark set under a policy deleted since keeps its id and the name it took when set, flagged deleted."""
    gone = TableMaintenancePolicyId.new()
    table = _managed(tables_repo, now)
    _mark_under(table, gone, now, name="nightly")
    out = ListTablesService(
        tables_repo, InMemoryCatalogDiscoveriesRepo(), InMemoryTableMaintenancePoliciesRepo()
    ).execute(ListTablesUseCaseInput())
    attention = out.items[0].operation_states["rewrite_data_files"]["needs_attention"]
    assert (attention["policy_id"], attention["policy_name"], attention["policy_deleted"]) == (
        gone.value,
        "nightly",
        True,
    )


def test_attention_mark_under_a_live_policy_shows_its_current_name(tables_repo, now):
    """The name kept on the mark is only a fallback: a policy that still exists is named as it is now."""
    policies = InMemoryTableMaintenancePoliciesRepo()
    nightly = TableMaintenancePolicy.create(
        TableMaintenancePolicyName(value="nightly-v2"), MaintenancePolicyContent.platform_default(), now
    )
    policies.create(nightly)
    table = _managed(tables_repo, now)
    _mark_under(table, nightly.id, now, name="nightly")
    out = GetTableService(tables_repo, InMemoryCatalogDiscoveriesRepo(), policies).execute(
        GetTableUseCaseInput(uuid="u-1")
    )
    attention = out.operation_states["rewrite_data_files"]["needs_attention"]
    assert (attention["policy_name"], attention["policy_deleted"]) == ("nightly-v2", False)
