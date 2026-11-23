"""Test the ListTableReconciliationsService."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from context.table_maintenance.application.domain.model.shared import TableMaintenancePolicyId, TableReconciliationId
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    MaintenancePolicyContent,
    TableMaintenancePolicy,
    TableMaintenancePolicyName,
)
from context.table_maintenance.application.port.inbound.table_reconciliation import (
    ListTableReconciliationsUseCaseInput,
)
from context.table_maintenance.application.service.table_reconciliation import (
    ListTableReconciliationsService,
    RecordTableReconciliationService,
)
from tests.context.table_maintenance.application.service.table_reconciliation.test_record_table_reconciliation_service import (  # noqa: E501
    _due_check,
    _input,
)
from tests.context.table_maintenance.fakes.in_memory_table_maintenance_policies_repo import (
    InMemoryTableMaintenancePoliciesRepo,
)
from tests.context.table_maintenance.fakes.in_memory_table_reconciliations_repo import (
    InMemoryTableReconciliationsRepo,
)

RUN_1 = "mr-00000000000000000000000001"
REC_1 = "rc-00000000000000000000000001"
RUN_2 = "mr-00000000000000000000000002"

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)


def test_maps_a_recorded_reconciliation_to_plain_items() -> None:
    """Enums become strings, measurements carry met, each operation's run_id is a string."""
    repo = InMemoryTableReconciliationsRepo()
    RecordTableReconciliationService(repo).execute(_input())

    output = ListTableReconciliationsService(repo, InMemoryTableMaintenancePoliciesRepo()).execute(
        ListTableReconciliationsUseCaseInput(table_uuid="table-1")
    )

    (item,) = output.items
    assert (item.reconciliation_id, item.outcome) == (REC_1, "planned")
    assert item.wake_reasons == {"schedule": 1}
    operation = item.operations[0]
    assert (operation.operation, operation.result, operation.run_id) == ("rewrite_data_files", "started", RUN_1)
    assert [(m.key, m.met) for m in operation.measurements] == [("small_files", True), ("data_bytes", None)]


def test_list_shows_the_run_of_each_operation() -> None:
    """Each started operation lists its own run; an operation that did not start lists none."""
    repo = InMemoryTableReconciliationsRepo()
    not_needed = {
        "operation": "rewrite_manifests",
        "verdict": "not_needed",
        "measurements": [],
        "next_eligible_at": None,
    }
    checks = (_due_check("rewrite_data_files"), _due_check("expire_snapshots"), not_needed)
    RecordTableReconciliationService(repo).execute(
        _input(checks=checks, run_ids={"rewrite_data_files": RUN_1, "expire_snapshots": RUN_2})
    )

    (item,) = (
        ListTableReconciliationsService(repo, InMemoryTableMaintenancePoliciesRepo())
        .execute(ListTableReconciliationsUseCaseInput(table_uuid="table-1"))
        .items
    )

    assert [(o.operation, o.run_id) for o in item.operations] == [
        ("rewrite_data_files", RUN_1),
        ("rewrite_manifests", None),
        ("expire_snapshots", RUN_2),
    ]
    assert not hasattr(item, "run_id")


def test_reconciliation_record_points_at_the_policy_id_and_lists_its_name() -> None:
    """A record keeps the policy's id; the listing names that policy by its id and its current name."""
    repo, policies = InMemoryTableReconciliationsRepo(), InMemoryTableMaintenancePoliciesRepo()
    nightly = TableMaintenancePolicy.create(
        TableMaintenancePolicyName(value="nightly"), MaintenancePolicyContent.platform_default(), NOW
    )
    policies.create(nightly)
    RecordTableReconciliationService(repo).execute(
        _input(policy_id=nightly.id.value, policy_name="nightly", policy_version=4)
    )

    (item,) = (
        ListTableReconciliationsService(repo, policies)
        .execute(ListTableReconciliationsUseCaseInput(table_uuid="table-1"))
        .items
    )

    assert repo.list_all()[0].policy_id == nightly.id
    assert (item.policy_id, item.policy_name, item.policy_version) == (nightly.id.value, "nightly", 4)
    assert item.policy_deleted is False


def test_reconciliation_keeps_the_policy_name_after_the_policy_is_deleted() -> None:
    """A record keeps the name its policy had when it was written, so it still reads after the delete."""
    repo, policies = InMemoryTableReconciliationsRepo(), InMemoryTableMaintenancePoliciesRepo()
    nightly = TableMaintenancePolicy.create(
        TableMaintenancePolicyName(value="nightly"), MaintenancePolicyContent.platform_default(), NOW
    )
    policies.create(nightly)
    RecordTableReconciliationService(repo).execute(
        _input(policy_id=nightly.id.value, policy_name="nightly", policy_version=4)
    )
    policies.delete(nightly.id)

    (item,) = (
        ListTableReconciliationsService(repo, policies)
        .execute(ListTableReconciliationsUseCaseInput(table_uuid="table-1"))
        .items
    )

    assert (item.policy_id, item.policy_name, item.policy_version) == (nightly.id.value, "nightly", 4)
    assert item.policy_deleted is True


def test_a_reconciliation_under_a_live_policy_lists_its_current_name() -> None:
    """The name kept on the record is only a fallback: a policy that still exists is named as it is now."""
    repo, policies = InMemoryTableReconciliationsRepo(), InMemoryTableMaintenancePoliciesRepo()
    policy_id = TableMaintenancePolicyId.new()
    policies.create(
        TableMaintenancePolicy(
            id=policy_id,
            name=TableMaintenancePolicyName(value="nightly-v2"),
            content=MaintenancePolicyContent.platform_default(),
            version=1,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    RecordTableReconciliationService(repo).execute(_input(policy_id=policy_id.value, policy_name="nightly"))

    (item,) = (
        ListTableReconciliationsService(repo, policies)
        .execute(ListTableReconciliationsUseCaseInput(table_uuid="table-1"))
        .items
    )

    assert (item.policy_name, item.policy_deleted) == ("nightly-v2", False)


def test_before_and_limit_are_passed_to_the_repo() -> None:
    """The cursor and the page size reach the repository."""
    repo = InMemoryTableReconciliationsRepo()
    record = RecordTableReconciliationService(repo)
    older, newer = TableReconciliationId.new().value, TableReconciliationId.new().value
    record.execute(
        _input(reconciliation_id=older, reconciled_at=NOW - timedelta(hours=1), run_ids={"rewrite_data_files": RUN_1})
    )
    record.execute(_input(reconciliation_id=newer, reconciled_at=NOW, run_ids={"rewrite_data_files": RUN_2}))

    output = ListTableReconciliationsService(repo, InMemoryTableMaintenancePoliciesRepo()).execute(
        ListTableReconciliationsUseCaseInput(table_uuid="table-1", before=NOW, limit=1)
    )

    assert [i.reconciliation_id for i in output.items] == [older]
