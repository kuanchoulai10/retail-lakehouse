from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any, cast
from unittest.mock import MagicMock

from temporalio import activity
from temporalio.worker import Worker

from adapter.inbound.temporal.activities import (
    DiscoveryActivities,
    MaintenanceActivities,
    ReconcileActivities,
    WorkflowSignalActivities,
)
from adapter.inbound.temporal.workflows import (
    CapacityLimiterWorkflow,
    DiscoveryWorkflow,
    MaintenanceWorkflow,
    TableReconcileWorkflow,
)
from adapter.temporal_contracts import activity_names
from bootstrap.configs import TemporalSettings
from bootstrap.container import (
    CAPACITY_LEASE_SECONDS,
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


def test_activities_carry_the_callback_url_and_capacity_settings():
    activities = _activities(callback_base_url="http://api:8000", capacity_limit=5)

    assert isinstance(activities.reconcile, ReconcileActivities)
    assert isinstance(activities.maintenance, MaintenanceActivities)
    assert isinstance(activities.discovery, DiscoveryActivities)
    assert isinstance(activities.workflow_signal, WorkflowSignalActivities)
    assert activities.reconcile._callback_base_url == "http://api:8000"  # noqa: SLF001
    assert activities.workflow_signal._capacity_limit == 5  # noqa: SLF001
    assert (
        activities.workflow_signal._capacity_lease_seconds  # noqa: SLF001
        == CAPACITY_LEASE_SECONDS
        == 21600
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
            TemporalSettings(task_queue="q"),
            executor=executor,
            max_concurrent_activities=2,
            worker_factory=factory,
        )

    assert factory.args == (client,)
    assert factory.kwargs["task_queue"] == "q"
    assert set(factory.kwargs["workflows"]) == {
        TableReconcileWorkflow,
        DiscoveryWorkflow,
        MaintenanceWorkflow,
        CapacityLimiterWorkflow,
    }
    names = {_activity_name(fn) for fn in factory.kwargs["activities"]}
    assert names == ALL_ACTIVITY_NAMES
    assert factory.kwargs["activity_executor"] is executor
    assert factory.kwargs["max_concurrent_activities"] == 2
