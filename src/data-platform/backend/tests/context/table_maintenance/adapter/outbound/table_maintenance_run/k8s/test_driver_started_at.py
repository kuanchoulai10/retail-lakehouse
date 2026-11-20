"""Test reading when the Spark driver container of an attempt started."""

from __future__ import annotations

from datetime import UTC, datetime

from kubernetes.client import (
    V1ContainerState,
    V1ContainerStateRunning,
    V1ContainerStateTerminated,
    V1ContainerStatus,
    V1ObjectMeta,
    V1Pod,
    V1PodStatus,
)

from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s import driver_started_at

STARTED = datetime(2026, 11, 20, 3, 0, 5, tzinfo=UTC)
EARLIER = datetime(2026, 11, 20, 2, 59, 0, tzinfo=UTC)


def _status(name: str, *, state: V1ContainerState | None = None, last_state: V1ContainerState | None = None):
    return V1ContainerStatus(
        name=name, image="i", image_id="i", ready=False, restart_count=0, state=state, last_state=last_state
    )


def _pod(role: str, *statuses: V1ContainerStatus) -> V1Pod:
    return V1Pod(
        metadata=V1ObjectMeta(name=f"{role}-pod", labels={"spark-role": role}),
        status=V1PodStatus(container_statuses=list(statuses)),
    )


def _running(at: datetime) -> V1ContainerState:
    return V1ContainerState(running=V1ContainerStateRunning(started_at=at))


def _terminated(at: datetime | None) -> V1ContainerState:
    return V1ContainerState(terminated=V1ContainerStateTerminated(exit_code=0, started_at=at))


def test_driver_start_from_a_running_container():
    """A driver container running since T gives T."""
    pod = _pod("driver", _status("spark-kubernetes-driver", state=_running(STARTED)))

    assert driver_started_at([pod]) == STARTED.isoformat()


def test_driver_start_from_a_terminated_container():
    """A driver container that already ended gives the time it started."""
    pod = _pod("driver", _status("spark-kubernetes-driver", state=_terminated(STARTED)))

    assert driver_started_at([pod]) == STARTED.isoformat()


def test_driver_start_from_the_last_state_of_a_restarted_container():
    """A driver container that restarted and waits again gives the start of its previous run."""
    waiting = V1ContainerState()
    pod = _pod("driver", _status("spark-kubernetes-driver", state=waiting, last_state=_terminated(STARTED)))

    assert driver_started_at([pod]) == STARTED.isoformat()


def test_a_running_state_wins_over_the_last_state():
    """The current run's start is preferred to the previous run's."""
    pod = _pod(
        "driver",
        _status("spark-kubernetes-driver", state=_running(STARTED), last_state=_terminated(EARLIER)),
    )

    assert driver_started_at([pod]) == STARTED.isoformat()


def test_only_the_driver_container_counts():
    """A sidecar container of the driver pod does not give the driver's start."""
    pod = _pod(
        "driver",
        _status("istio-proxy", state=_running(EARLIER)),
        _status("spark-kubernetes-driver", state=_running(STARTED)),
    )

    assert driver_started_at([pod]) == STARTED.isoformat()


def test_executor_pods_do_not_count():
    """An attempt with only an executor running has no driver start."""
    pod = _pod("executor", _status("spark-kubernetes-executor", state=_running(STARTED)))

    assert driver_started_at([pod]) is None


def test_no_driver_pod_is_none():
    """An attempt without pods has no driver start."""
    assert driver_started_at([]) is None


def test_a_driver_that_has_not_started_is_none():
    """A driver container that is still waiting has no start."""
    pod = _pod("driver", _status("spark-kubernetes-driver", state=V1ContainerState()))

    assert driver_started_at([pod]) is None
    assert driver_started_at([_pod("driver")]) is None
    assert driver_started_at([V1Pod(metadata=V1ObjectMeta(name="d", labels={"spark-role": "driver"}))]) is None
