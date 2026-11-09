"""Test the RecordTableReconciliationService."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

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

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)


def _due_check(operation: str = "rewrite_data_files") -> dict:
    return {
        "operation": operation,
        "verdict": "due",
        "combine": "all",
        "measurements": [
            {"key": "small_files", "observed": 12, "unit": "count", "threshold": 10, "comparison": ">=", "met": True},
            {"key": "data_bytes", "observed": 5, "unit": "bytes", "threshold": None, "comparison": None, "met": None},
        ],
        "next_eligible_at": None,
    }


def _input(**overrides: object) -> RecordTableReconciliationUseCaseInput:
    base = RecordTableReconciliationUseCaseInput(
        reconciliation_id="rec-1",
        table_uuid="table-1",
        reconciled_at=NOW,
        wake_reasons={"schedule": 1},
        dry_run=False,
        status="planned",
        skip_reason=None,
        checks=[_due_check()],
        run_id="run-1",
        run_start_failed=False,
    )
    return replace(base, **overrides)


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
    saved = repo.get(TableReconciliationId("rec-1"))
    assert saved is not None
    assert saved.run_id is not None
    assert saved.run_id.value == "run-1"
    assert saved.outcome is ReconciliationOutcome.PLANNED
    assert saved.operations[0].result is OperationResult.STARTED
    assert saved.operations[0].measurements[0].met is True


def test_dry_run_due_becomes_would_start(
    service: RecordTableReconciliationService, repo: InMemoryTableReconciliationsRepo
) -> None:
    """Dry run due becomes would start."""
    service.execute(_input(dry_run=True, run_id=None))

    saved = repo.get(TableReconciliationId("rec-1"))
    assert saved is not None
    assert saved.operations[0].result is OperationResult.WOULD_START
    assert saved.run_id is None


def test_failed_start_records_start_failed_without_run(
    service: RecordTableReconciliationService, repo: InMemoryTableReconciliationsRepo
) -> None:
    """Failed start records start failed without run."""
    service.execute(_input(run_id=None, run_start_failed=True))

    saved = repo.get(TableReconciliationId("rec-1"))
    assert saved is not None
    assert saved.operations[0].result is OperationResult.START_FAILED
    assert saved.run_id is None


def test_other_verdicts_map_by_name_and_next_eligible_is_parsed(
    service: RecordTableReconciliationService, repo: InMemoryTableReconciliationsRepo
) -> None:
    """Other verdicts map by name and next eligible is parsed."""
    cooling = {
        "operation": "expire_snapshots",
        "verdict": "cooling_down",
        "combine": "any",
        "measurements": [],
        "next_eligible_at": "2026-11-11T00:00:00+00:00",
    }
    off = {**cooling, "operation": "remove_orphan_files", "verdict": "off", "next_eligible_at": None}
    not_due = {**cooling, "operation": "rewrite_manifests", "verdict": "not_needed", "next_eligible_at": None}
    unchecked = {**not_due, "operation": "rewrite_data_files", "verdict": "not_checked", "combine": "all"}
    service.execute(_input(checks=[cooling, off, not_due, unchecked], run_id=None))

    saved = repo.get(TableReconciliationId("rec-1"))
    assert saved is not None
    by_op = {op.operation.value: op for op in saved.operations}
    assert by_op["expire_snapshots"].result is OperationResult.COOLING_DOWN
    assert by_op["expire_snapshots"].next_eligible_at == datetime(2026, 11, 11, tzinfo=UTC)
    assert by_op["remove_orphan_files"].result is OperationResult.OFF
    assert by_op["rewrite_manifests"].result is OperationResult.NOT_NEEDED
    assert by_op["rewrite_data_files"].result is OperationResult.NOT_CHECKED


def test_skip_is_recorded_with_reason(
    service: RecordTableReconciliationService, repo: InMemoryTableReconciliationsRepo
) -> None:
    """Skip is recorded with reason."""
    service.execute(_input(status="skip", skip_reason="table is paused", checks=[], run_id=None))

    saved = repo.get(TableReconciliationId("rec-1"))
    assert saved is not None
    assert saved.outcome is ReconciliationOutcome.SKIPPED
    assert saved.skip_reason == "table is paused"
    assert saved.operations == ()


def test_records_older_than_thirty_days_are_purged(
    service: RecordTableReconciliationService, repo: InMemoryTableReconciliationsRepo
) -> None:
    """Records older than thirty days are purged."""
    service.execute(_input(reconciliation_id="old", reconciled_at=NOW - timedelta(days=31), run_id=None, dry_run=True))
    service.execute(
        _input(reconciliation_id="recent", reconciled_at=NOW - timedelta(days=29), run_id=None, dry_run=True)
    )

    service.execute(_input(reconciliation_id="now", run_id=None, dry_run=True))

    assert repo.get(TableReconciliationId("old")) is None
    assert repo.get(TableReconciliationId("recent")) is not None
    assert repo.get(TableReconciliationId("now")) is not None


def test_purge_leaves_other_tables_alone(
    service: RecordTableReconciliationService, repo: InMemoryTableReconciliationsRepo
) -> None:
    """Purge leaves other tables alone."""
    service.execute(
        _input(
            reconciliation_id="other",
            table_uuid="table-2",
            reconciled_at=NOW - timedelta(days=40),
            run_id=None,
            dry_run=True,
        )
    )

    service.execute(_input(run_id=None, dry_run=True))

    assert repo.get(TableReconciliationId("other")) is not None


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
        {"checks": [{**_due_check(), "verdict": "bogus"}]},
        {"checks": [{**_due_check(), "verdict": "not_due"}]},
        {"checks": [{**_due_check(), "verdict": "cooldown"}]},
        {"checks": [{**_due_check(), "verdict": "disabled"}]},
        {"checks": [{**_due_check(), "measurements": ["x"]}]},
        {"run_id": None},
        {"status": "weird"},
        {"status": "skip", "skip_reason": None, "checks": [], "run_id": None},
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
    service.execute(_input(reconciliation_id="old", reconciled_at=NOW - timedelta(days=31), run_id=None, dry_run=True))

    again = service.execute(_input())

    assert again.recorded is False
    assert repo.get(TableReconciliationId("old")) is None


def test_discovery_scan_is_a_known_wake_reason(
    service: RecordTableReconciliationService, repo: InMemoryTableReconciliationsRepo
) -> None:
    """A discovery scan is recorded as its own wake reason."""
    service.execute(_input(wake_reasons={"discovery_scan": 1}))

    saved = repo.get(TableReconciliationId("rec-1"))
    assert saved is not None
    assert {reason.value: count for reason, count in saved.wake_reasons.items()} == {"discovery_scan": 1}
