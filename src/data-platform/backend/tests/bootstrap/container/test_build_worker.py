"""Test that the Temporal worker is built with every workflow and activity."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import MagicMock

from temporalio import activity

from bootstrap.container import (
    build_activities,
    build_repositories,
    build_use_cases,
    build_worker,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.compaction_round import (
    CompactionRoundActivity,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.shared import (
    TASK_QUEUE,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_discovery import (
    TableDiscoveryActivity,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    TableMaintenanceActivity,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_reconciliation import (
    TableReconciliationActivity,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.activities import (
    CompactionRoundActivities,
    TableDiscoveryActivities,
    TableMaintenanceActivities,
    TableReconciliationActivities,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows import (
    CompactionRoundWorkflow,
    TableDiscoveryWorkflow,
    TableMaintenanceAdmissionWorkflow,
    TableMaintenanceWorkflow,
    TableReconciliationWorkflow,
)
from tests.bootstrap.container.container_support import (
    NOW,
    fake_gateways,
    platform_settings,
    sqlite_engine,
    sqlite_settings,
)

if TYPE_CHECKING:
    from temporalio.worker import Worker

# Every member of every workflow's activity enum, not one name, is under test.
ALL_ACTIVITY_NAMES = {
    str(member)
    for enum in (
        CompactionRoundActivity,
        TableDiscoveryActivity,
        TableMaintenanceActivity,
        TableReconciliationActivity,
    )
    for member in enum
}


def _activity_name(fn: Any) -> str:  # noqa: ANN401
    name = activity._Definition.must_from_callable(fn).name  # noqa: SLF001
    assert name is not None
    return name


def _activities(**overrides: object):
    use_cases = build_use_cases(
        build_repositories(sqlite_engine()), fake_gateways(), platform_settings=platform_settings(), clock=lambda: NOW
    )
    return build_activities(use_cases, MagicMock(), sqlite_settings(**overrides))


def test_activities_cover_every_activity_name_once():
    """The built activities cover every activity name exactly once."""
    callables = _activities().callables()

    names = [_activity_name(fn) for fn in callables]
    assert sorted(names) == sorted(ALL_ACTIVITY_NAMES)


def test_activities_carry_the_callback_url_and_admission_settings():
    """The activity groups are built with the callback URL, the admission settings and the attempt deadline."""
    activities = _activities(
        callback_base_url="http://api:8000",
        admission_limit=5,
        maintenance_attempt_deadline_seconds=120,
        maintenance_max_attempts=4,
    )

    assert isinstance(activities.reconciliation, TableReconciliationActivities)
    assert isinstance(activities.maintenance, TableMaintenanceActivities)
    assert isinstance(activities.discovery, TableDiscoveryActivities)
    assert isinstance(activities.compaction_round, CompactionRoundActivities)
    assert activities.maintenance._callback_base_url == "http://api:8000"  # noqa: SLF001
    assert activities.maintenance._admission_limit == 5  # noqa: SLF001
    assert activities.maintenance._admission_lease_seconds == 1020  # noqa: SLF001
    assert activities.reconciliation._attempt_deadline_seconds == 120  # noqa: SLF001
    assert activities.reconciliation._max_attempts == 4  # noqa: SLF001


class RecordingWorkerFactory:
    """Worker factory stub that records how it is called."""

    def __init__(self) -> None:
        """Start with no recorded arguments."""
        self.args: tuple[Any, ...] = ()
        self.kwargs: dict[str, Any] = {}

    def __call__(self, *args: Any, **kwargs: Any) -> Worker:  # noqa: ANN401
        """Record the arguments and return a placeholder worker."""
        self.args = args
        self.kwargs = kwargs
        return cast("Worker", object())


def test_worker_registers_all_workflows_and_activities():
    """The worker is created for the client on the table maintenance queue with all workflows and activities."""
    factory = RecordingWorkerFactory()
    client = MagicMock()
    with ThreadPoolExecutor(max_workers=2) as executor:
        build_worker(
            client,
            _activities(),
            executor=executor,
            max_concurrent_activities=2,
            worker_factory=factory,
        )

    assert factory.args == (client,)
    assert factory.kwargs["task_queue"] == TASK_QUEUE == "table-maintenance"
    assert set(factory.kwargs["workflows"]) == {
        TableReconciliationWorkflow,
        TableDiscoveryWorkflow,
        TableMaintenanceWorkflow,
        TableMaintenanceAdmissionWorkflow,
        CompactionRoundWorkflow,
    }
    names = {_activity_name(fn) for fn in factory.kwargs["activities"]}
    assert names == ALL_ACTIVITY_NAMES
    assert factory.kwargs["activity_executor"] is executor
    assert factory.kwargs["max_concurrent_activities"] == 2
