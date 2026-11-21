"""Test the service that raises the priority of a maintenance run in flight."""

from __future__ import annotations

import pytest

from context.table_maintenance.application.domain.model.shared import ComputeSize, MaintenanceOperation, TablePriority
from context.table_maintenance.application.domain.model.table import Table, TableId, TableName
from context.table_maintenance.application.domain.model.table_discovery_rules import TableDiscoveryRuleId
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    TableMaintenanceRun,
    TableMaintenanceRunId,
    TriggerType,
)
from context.table_maintenance.application.exceptions import NotFoundError, ValidationError
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    RaiseTableMaintenanceRunPriorityUseCaseInput,
)
from context.table_maintenance.application.service.table_maintenance_run import (
    RaiseTableMaintenanceRunPriorityService,
)
from tests.context.table_maintenance.fakes.track_calls import track_calls

RUN_1 = "mr-00000000000000000000000001"
UNKNOWN_RUN = "mr-7zzzzzzzzzzzzzzzzzzzzzzzzz"
RDF = MaintenanceOperation.REWRITE_DATA_FILES


@pytest.fixture
def table(tables_repo, now) -> Table:
    """Provide a stored table at P1."""
    t = Table.register(
        TableId("u-1"),
        TableName(catalog="iceberg", namespace="sales", table="orders"),
        TableDiscoveryRuleId.new(),
        now,
    )
    t.set_priority(TablePriority.P1, now)
    tables_repo.create(t)
    return t


def _stored_run(runs_repo, now, priority: TablePriority, *, started: bool = True) -> TableMaintenanceRun:
    """Store a run at ``priority`` whose first attempt is queued, or that is pending when not ``started``."""
    r = TableMaintenanceRun.create(
        TableMaintenanceRunId(RUN_1),
        TableId("u-1"),
        TriggerType.SCHEDULED,
        RDF,
        now,
        execution_ref="wf-1",
        priority=priority,
    )
    if started:
        r.start_attempt(1, None, now, size=ComputeSize.S)
    runs_repo.create(r)
    return r


@pytest.fixture
def run(runs_repo, now) -> TableMaintenanceRun:
    """Provide a stored run at P3 whose first attempt is queued."""
    return _stored_run(runs_repo, now, TablePriority.P3)


@pytest.fixture
def run_at_p1(runs_repo, now) -> TableMaintenanceRun:
    """Provide a stored run at P1 whose first attempt is queued."""
    return _stored_run(runs_repo, now, TablePriority.P1)


@pytest.fixture
def service(runs_repo, tables_repo) -> RaiseTableMaintenanceRunPriorityService:
    """Provide the service over the in-memory repos."""
    return RaiseTableMaintenanceRunPriorityService(runs_repo, tables_repo)


def _input(now, priority: str | None, run_id: str = RUN_1) -> RaiseTableMaintenanceRunPriorityUseCaseInput:
    return RaiseTableMaintenanceRunPriorityUseCaseInput(run_id=run_id, priority=priority, now=now)


def test_service_raises_to_the_given_priority(service, runs_repo, run, now):
    """A priority that outranks the run's raises it and the run is saved."""
    out = service.execute(_input(now, "P0"))

    assert (out.priority, out.raised) == ("P0", True)
    assert runs_repo.get(TableMaintenanceRunId(RUN_1)).priority is TablePriority.P0


def test_service_raises_to_the_tables_priority_when_none_given(service, runs_repo, run, table, now):
    """No priority means the table's current one."""
    saved: list[tuple[str, str]] = []
    track_calls(runs_repo, "update", "runs.update", saved, lambda r: r.id.value)

    out = service.execute(_input(now, None))

    assert (out.priority, out.raised) == ("P1", True)
    assert saved == [("runs.update", RUN_1)]
    assert runs_repo.get(TableMaintenanceRunId(RUN_1)).priority is TablePriority.P1


def test_service_does_not_lower_or_save(service, runs_repo, run_at_p1, now):
    """An equal or lower priority leaves the run alone and saves nothing."""
    saved: list[tuple[str, str]] = []
    track_calls(runs_repo, "update", "runs.update", saved, lambda r: r.id.value)

    out = service.execute(_input(now, "P2"))

    assert (out.priority, out.raised) == ("P1", False)
    assert saved == []


def test_service_without_a_table_raises_nothing(service, runs_repo, run, now):
    """No priority and no table: the run keeps its priority."""
    saved: list[tuple[str, str]] = []
    track_calls(runs_repo, "update", "runs.update", saved, lambda r: r.id.value)

    out = service.execute(_input(now, None))

    assert (out.priority, out.raised) == ("P3", False)
    assert saved == []


def test_service_refuses_p9(service, run, now):
    """An unknown priority is a validation error."""
    with pytest.raises(ValidationError):
        service.execute(_input(now, "P9"))


def test_service_refuses_an_unknown_run(service, now):
    """An unknown run is not found."""
    with pytest.raises(NotFoundError):
        service.execute(_input(now, "P0", run_id=UNKNOWN_RUN))


def test_service_raises_a_pending_run(service, runs_repo, now):
    """A run that has not started yet is raised, so its first submit goes at the new priority."""
    _stored_run(runs_repo, now, TablePriority.P3, started=False)

    out = service.execute(_input(now, "P0"))

    assert (out.priority, out.raised) == ("P0", True)
    assert runs_repo.get(TableMaintenanceRunId(RUN_1)).priority is TablePriority.P0


def test_service_does_not_raise_a_succeeded_run(service, runs_repo, run, now):
    """A run that succeeded keeps its priority and is not saved."""
    run.succeed(1, {}, now)
    saved: list[tuple[str, str]] = []
    track_calls(runs_repo, "update", "runs.update", saved, lambda r: r.id.value)

    out = service.execute(_input(now, "P0"))

    assert (out.priority, out.raised) == ("P3", False)
    assert saved == []
