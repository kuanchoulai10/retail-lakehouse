from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any, cast
from unittest.mock import MagicMock

from temporalio import activity
from temporalio.worker import Worker

from adapter.hybrid.temporal.inbound.activities import (
    TableDiscoveryActivities,
    TableMaintenanceActivities,
    TableReconciliationActivities,
    WorkflowSignalActivities,
)
from adapter.hybrid.temporal.inbound.workflows import (
    TableMaintenanceAdmissionWorkflow,
    TableDiscoveryWorkflow,
    TableMaintenanceWorkflow,
    TableReconciliationWorkflow,
)
from adapter.hybrid.temporal.contracts import activity_names
from adapter.hybrid.temporal.contracts.workflow_ids import TASK_QUEUE
from bootstrap.container import (
    ADMISSION_LEASE_SECONDS,
    build_activities,
    build_repositories,
    build_use_cases,
    build_worker,
)
from tests.bootstrap.container.container_support import (
    NOW,
    fake_gateways,
    sqlite_engine,
    sqlite_settings,
)

ALL_ACTIVITY_NAMES = {
    value
    for name, value in vars(activity_names).items()
    if name.isupper() and isinstance(value, str)
}


def _activity_name(fn: Any) -> str:  # noqa: ANN401
    name = activity._Definition.must_from_callable(fn).name  # noqa: SLF001
    assert name is not None
    return name


def _activities(**overrides: object):
    use_cases = build_use_cases(
        build_repositories(sqlite_engine()), fake_gateways(), clock=lambda: NOW
    )
    return build_activities(use_cases, MagicMock(), sqlite_settings(**overrides))


def test_activities_cover_every_activity_name_once():
    callables = _activities().callables()

    names = [_activity_name(fn) for fn in callables]
    assert sorted(names) == sorted(ALL_ACTIVITY_NAMES)


def test_activities_carry_the_callback_url_and_admission_settings():
    activities = _activities(callback_base_url="http://api:8000", admission_limit=5)

    assert isinstance(activities.reconciliation, TableReconciliationActivities)
    assert isinstance(activities.maintenance, TableMaintenanceActivities)
    assert isinstance(activities.discovery, TableDiscoveryActivities)
    assert isinstance(activities.workflow_signal, WorkflowSignalActivities)
    assert activities.reconciliation._callback_base_url == "http://api:8000"  # noqa: SLF001
    assert activities.workflow_signal._admission_limit == 5  # noqa: SLF001
    assert (
        activities.workflow_signal._admission_lease_seconds  # noqa: SLF001
        == ADMISSION_LEASE_SECONDS
        == 22500
    )


class RecordingWorkerFactory:
    def __init__(self) -> None:
        self.args: tuple[Any, ...] = ()
        self.kwargs: dict[str, Any] = {}

    def __call__(self, *args: Any, **kwargs: Any) -> Worker:  # noqa: ANN401
        self.args = args
        self.kwargs = kwargs
        return cast("Worker", object())


def test_worker_registers_all_workflows_and_activities():
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
    }
    names = {_activity_name(fn) for fn in factory.kwargs["activities"]}
    assert names == ALL_ACTIVITY_NAMES
    assert factory.kwargs["activity_executor"] is executor
    assert factory.kwargs["max_concurrent_activities"] == 2
