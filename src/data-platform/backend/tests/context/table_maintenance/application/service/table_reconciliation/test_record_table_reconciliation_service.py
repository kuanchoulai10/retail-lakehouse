"""Test the RecordTableReconciliationService."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from context.table_maintenance.application.domain.model.table_maintenance_run import (
    TableMaintenanceRunId,
)
from context.table_maintenance.application.domain.model.table_reconciliation import (
    OperationResult,
    ReconciliationOutcome,
    TableReconciliationId,
)
from context.table_maintenance.application.exceptions import ValidationError
from context.table_maintenance.application.port.inbound.table_reconciliation import (
    RecordTableReconciliationUseCaseInput,
)
from context.table_maintenance.application.service.table_reconciliation import (
    RecordTableReconciliationService,
)
from tests.context.table_maintenance.fakes.in_memory_table_reconciliations_repo import (
    InMemoryTableReconciliationsRepo,
)

RUN_1 = "mr-00000000000000000000000001"
RUN_2 = "mr-00000000000000000000000002"
REC_1 = "rc-00000000000000000000000001"
OLD_REC = "rc-00000000000000000000000002"
RECENT_REC = "rc-00000000000000000000000003"
NOW_REC = "rc-00000000000000000000000004"
OTHER_REC = "rc-00000000000000000000000005"
DEFAULT_POLICY_ID = "mp-00000000000000000000000000"
NIGHTLY = "mp-00000000000000000000000004"

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)


def _due_check(operation: str = "rewrite_data_files") -> dict:
    return {
        "operation": operation,
        "verdict": "due",
        "measurements": [
            {"key": "small_files", "observed": 12, "unit": "count", "threshold": 10, "comparison": ">=", "met": True},
            {"key": "data_bytes", "observed": 5, "unit": "bytes", "threshold": None, "comparison": None, "met": None},
        ],
        "next_eligible_at": None,
    }


def _input(**overrides: object) -> RecordTableReconciliationUseCaseInput:
    base = RecordTableReconciliationUseCaseInput(
        reconciliation_id=REC_1,
        table_uuid="table-1",
        reconciled_at=NOW,
        wake_reasons={"schedule": 1},
        dry_run=False,
        status="planned",
        skip_reason=None,
        checks=(_due_check(),),
        run_ids={"rewrite_data_files": RUN_1},
        run_start_failed=False,
        policy_id=DEFAULT_POLICY_ID,
        policy_name="default",
        policy_version=3,
        policy_target=None,
    )
    return RecordTableReconciliationUseCaseInput(**(base.model_dump() | overrides))


@pytest.fixture
def repo() -> InMemoryTableReconciliationsRepo:
    """Provide an in-memory reconciliations repository."""
    return InMemoryTableReconciliationsRepo()


@pytest.fixture
def service(repo: InMemoryTableReconciliationsRepo) -> RecordTableReconciliationService:
    """Provide the service under test."""
    return RecordTableReconciliationService(repo)


def test_started_due_operations_link_the_run(
    service: RecordTableReconciliationService, repo: InMemoryTableReconciliationsRepo
) -> None:
    """Started due operations link the run."""
    out = service.execute(_input())

    assert out.recorded is True
    saved = repo.get(TableReconciliationId(REC_1))
    assert saved is not None
    assert saved.operations[0].run_id is not None
    assert saved.operations[0].run_id.value == RUN_1
    assert saved.outcome is ReconciliationOutcome.PLANNED
    assert saved.operations[0].result is OperationResult.STARTED
    assert saved.operations[0].measurements[0].met is True


def test_record_links_each_started_operation_to_its_run(
    service: RecordTableReconciliationService, repo: InMemoryTableReconciliationsRepo
) -> None:
    """Each started operation keeps the id of its own run; the others keep none."""
    checks = (
        _due_check("rewrite_data_files"),
        _due_check("expire_snapshots"),
        {"operation": "rewrite_manifests", "verdict": "not_needed", "measurements": [], "next_eligible_at": None},
    )
    service.execute(_input(checks=checks, run_ids={"rewrite_data_files": RUN_1, "expire_snapshots": RUN_2}))

    saved = repo.get(TableReconciliationId(REC_1))
    assert saved is not None
    by_op = {op.operation.value: op for op in saved.operations}
    assert (by_op["rewrite_data_files"].result, by_op["rewrite_data_files"].run_id) == (
        OperationResult.STARTED,
        TableMaintenanceRunId(RUN_1),
    )
    assert (by_op["expire_snapshots"].result, by_op["expire_snapshots"].run_id) == (
        OperationResult.STARTED,
        TableMaintenanceRunId(RUN_2),
    )
    assert by_op["rewrite_manifests"].run_id is None


def test_record_refuses_a_run_for_an_operation_not_planned(service: RecordTableReconciliationService) -> None:
    """A run id for an operation the plan did not start is refused."""
    with pytest.raises(ValidationError, match="not a planned operation"):
        service.execute(_input(run_ids={"rewrite_data_files": RUN_1, "rewrite_manifests": RUN_2}))


def test_record_refuses_a_run_for_an_operation_that_is_not_due(service: RecordTableReconciliationService) -> None:
    """Planned means due: an operation that was assessed but not due cannot have started a run."""
    not_needed = {
        "operation": "rewrite_manifests",
        "verdict": "not_needed",
        "measurements": [],
        "next_eligible_at": None,
    }
    checks = (_due_check(), not_needed)

    with pytest.raises(ValidationError, match="not a planned operation"):
        service.execute(_input(checks=checks, run_ids={"rewrite_data_files": RUN_1, "rewrite_manifests": RUN_2}))


def test_dry_run_due_becomes_would_start(
    service: RecordTableReconciliationService, repo: InMemoryTableReconciliationsRepo
) -> None:
    """Dry run due becomes would start."""
    service.execute(_input(dry_run=True, run_ids={}))

    saved = repo.get(TableReconciliationId(REC_1))
    assert saved is not None
    assert saved.operations[0].result is OperationResult.WOULD_START
    assert saved.operations[0].run_id is None


def test_failed_start_records_start_failed_without_run(
    service: RecordTableReconciliationService, repo: InMemoryTableReconciliationsRepo
) -> None:
    """Failed start records start failed without run."""
    service.execute(_input(run_ids={}, run_start_failed=True))

    saved = repo.get(TableReconciliationId(REC_1))
    assert saved is not None
    assert saved.operations[0].result is OperationResult.START_FAILED
    assert saved.operations[0].run_id is None


def test_other_verdicts_map_by_name_and_next_eligible_is_parsed(
    service: RecordTableReconciliationService, repo: InMemoryTableReconciliationsRepo
) -> None:
    """Other verdicts map by name and next eligible is parsed."""
    cooling = {
        "operation": "expire_snapshots",
        "verdict": "cooling_down",
        "measurements": [],
        "next_eligible_at": "2026-11-11T00:00:00+00:00",
    }
    off = {**cooling, "operation": "remove_orphan_files", "verdict": "off", "next_eligible_at": None}
    not_due = {**cooling, "operation": "rewrite_manifests", "verdict": "not_needed", "next_eligible_at": None}
    unchecked = {**not_due, "operation": "rewrite_data_files", "verdict": "not_checked"}
    service.execute(_input(checks=(cooling, off, not_due, unchecked), run_ids={}))

    saved = repo.get(TableReconciliationId(REC_1))
    assert saved is not None
    by_op = {op.operation.value: op for op in saved.operations}
    assert by_op["expire_snapshots"].result is OperationResult.COOLING_DOWN
    assert by_op["expire_snapshots"].next_eligible_at == datetime(2026, 11, 11, tzinfo=UTC)
    assert by_op["remove_orphan_files"].result is OperationResult.OFF
    assert by_op["rewrite_manifests"].result is OperationResult.NOT_NEEDED
    assert by_op["rewrite_data_files"].result is OperationResult.NOT_CHECKED


def test_waiting_for_writes_is_recorded(
    service: RecordTableReconciliationService, repo: InMemoryTableReconciliationsRepo
) -> None:
    """A waiting for writes check is recorded without a run, with the time it may run again."""
    waiting = {
        "operation": "rewrite_data_files",
        "verdict": "waiting_for_writes",
        "measurements": [],
        "next_eligible_at": "2026-11-10T12:02:00+00:00",
    }
    service.execute(_input(checks=(waiting,), run_ids={}))

    saved = repo.get(TableReconciliationId(REC_1))
    assert saved is not None
    assert saved.operations[0].run_id is None
    assert saved.operations[0].result is OperationResult.WAITING_FOR_WRITES
    assert saved.operations[0].next_eligible_at == datetime(2026, 11, 10, 12, 2, tzinfo=UTC)


def test_skip_is_recorded_with_reason(
    service: RecordTableReconciliationService, repo: InMemoryTableReconciliationsRepo
) -> None:
    """Skip is recorded with reason."""
    service.execute(_input(status="skip", skip_reason="table is paused", checks=(), run_ids={}))

    saved = repo.get(TableReconciliationId(REC_1))
    assert saved is not None
    assert saved.outcome is ReconciliationOutcome.SKIPPED
    assert saved.skip_reason == "table is paused"
    assert saved.operations == ()


def test_records_older_than_thirty_days_are_purged(
    service: RecordTableReconciliationService, repo: InMemoryTableReconciliationsRepo
) -> None:
    """Records older than thirty days are purged."""
    service.execute(_input(reconciliation_id=OLD_REC, reconciled_at=NOW - timedelta(days=31), run_ids={}, dry_run=True))
    service.execute(
        _input(reconciliation_id=RECENT_REC, reconciled_at=NOW - timedelta(days=29), run_ids={}, dry_run=True)
    )

    service.execute(_input(reconciliation_id=NOW_REC, run_ids={}, dry_run=True))

    assert repo.get(TableReconciliationId(OLD_REC)) is None
    assert repo.get(TableReconciliationId(RECENT_REC)) is not None
    assert repo.get(TableReconciliationId(NOW_REC)) is not None


def test_purge_leaves_other_tables_alone(
    service: RecordTableReconciliationService, repo: InMemoryTableReconciliationsRepo
) -> None:
    """Purge leaves other tables alone."""
    service.execute(
        _input(
            reconciliation_id=OTHER_REC,
            table_uuid="table-2",
            reconciled_at=NOW - timedelta(days=40),
            run_ids={},
            dry_run=True,
        )
    )

    service.execute(_input(run_ids={}, dry_run=True))

    assert repo.get(TableReconciliationId(OTHER_REC)) is not None


def test_recording_twice_keeps_one_record(
    service: RecordTableReconciliationService, repo: InMemoryTableReconciliationsRepo
) -> None:
    """Recording twice keeps one record."""
    first = service.execute(_input())
    second = service.execute(_input())

    assert first.recorded is True
    assert second.recorded is False
    assert len(repo.list_all()) == 1


@pytest.mark.parametrize(
    "overrides",
    [
        {"wake_reasons": {"bogus": 1}},
        {"wake_reasons": {}},
        {"checks": ({**_due_check(), "verdict": "bogus"},)},
        {"checks": ({**_due_check(), "verdict": "not_due"},)},
        {"checks": ({**_due_check(), "verdict": "cooldown"},)},
        {"checks": ({**_due_check(), "verdict": "disabled"},)},
        {"checks": ({**_due_check(), "measurements": ["x"]},)},
        {"run_ids": {}},
        {"run_ids": {"rewrite_manifests": RUN_1}},
        {"status": "weird"},
        {"status": "skip", "skip_reason": None, "checks": (), "run_ids": {}},
        {"policy_id": "nightly"},
    ],
)
def test_invalid_input_is_rejected(service: RecordTableReconciliationService, overrides: dict) -> None:
    """Invalid input is rejected."""
    with pytest.raises(ValidationError):
        service.execute(_input(**overrides))


def test_noop_path_still_purges_old_records(
    service: RecordTableReconciliationService, repo: InMemoryTableReconciliationsRepo
) -> None:
    """A retried record that already exists still purges records past retention."""
    service.execute(_input())
    service.execute(_input(reconciliation_id=OLD_REC, reconciled_at=NOW - timedelta(days=31), run_ids={}, dry_run=True))

    again = service.execute(_input())

    assert again.recorded is False
    assert repo.get(TableReconciliationId(OLD_REC)) is None


def test_table_managed_is_a_known_wake_reason(
    service: RecordTableReconciliationService, repo: InMemoryTableReconciliationsRepo
) -> None:
    """A table that became managed is recorded as its own wake reason."""
    service.execute(_input(wake_reasons={"table_managed": 1}))

    saved = repo.get(TableReconciliationId(REC_1))
    assert saved is not None
    assert {reason.value: count for reason, count in saved.wake_reasons.items()} == {"table_managed": 1}


def test_record_keeps_policy_id_version_and_target(
    service: RecordTableReconciliationService, repo: InMemoryTableReconciliationsRepo
) -> None:
    """The record keeps the plan's policy id, its name then, the version and the target it was attached to."""
    service.execute(
        _input(
            policy_id=NIGHTLY,
            policy_name="nightly",
            policy_version=4,
            policy_target={"type": "namespace", "path": ["prod", "sales"]},
        )
    )

    saved = repo.get(TableReconciliationId(REC_1))
    assert saved is not None
    assert (saved.policy_id.value, saved.policy_name.value, saved.policy_version) == (NIGHTLY, "nightly", 4)
    assert saved.policy_target is not None
    assert (saved.policy_target.type.value, saved.policy_target.path) == ("namespace", ("prod", "sales"))


def test_record_keeps_a_table_target_with_its_uuid(
    service: RecordTableReconciliationService, repo: InMemoryTableReconciliationsRepo
) -> None:
    """A table target arrives with the table's uuid, as the plan reports it."""
    target = {"type": "table", "path": ["prod", "sales", "orders"], "table_uuid": "table-1"}
    service.execute(_input(policy_target=target))

    saved = repo.get(TableReconciliationId(REC_1))
    assert saved is not None
    assert saved.policy_target is not None
    assert saved.policy_target.table_uuid == "table-1"


def test_default_fallback_records_no_target(
    service: RecordTableReconciliationService, repo: InMemoryTableReconciliationsRepo
) -> None:
    """The default policy with nothing attached records a null target."""
    service.execute(_input(policy_target=None))

    saved = repo.get(TableReconciliationId(REC_1))
    assert saved is not None
    assert saved.policy_target is None


def test_a_malformed_policy_target_is_a_validation_error(service: RecordTableReconciliationService) -> None:
    """A target that is not a valid policy target is rejected."""
    with pytest.raises(ValidationError):
        service.execute(_input(policy_target={"type": "galaxy", "path": ["x"]}))
