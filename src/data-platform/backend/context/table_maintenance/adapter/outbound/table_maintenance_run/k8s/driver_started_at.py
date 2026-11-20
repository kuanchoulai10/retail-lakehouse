"""Define the driver_started_at function."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from kubernetes.client import V1ContainerStatus, V1Pod

SPARK_ROLE_LABEL = "spark-role"
DRIVER_ROLE = "driver"
DRIVER_CONTAINER = "spark-kubernetes-driver"


def driver_started_at(pods: Sequence[V1Pod]) -> str | None:
    """Return the ISO-8601 time the Spark driver container started, or None when it has not.

    The driver pod is the one labelled ``spark-role=driver``; its ``spark-kubernetes-driver``
    container gives the time of its current run, else of the run that ended, else of its
    previous run (a restarted container). Executor pods and sidecar containers do not count.
    """
    for pod in pods:
        if (pod.metadata.labels or {}).get(SPARK_ROLE_LABEL) != DRIVER_ROLE:
            continue
        for status in (pod.status.container_statuses if pod.status else None) or []:
            if status.name == DRIVER_CONTAINER and (started := _started_at(status)) is not None:
                return started.isoformat()
    return None


def _started_at(status: V1ContainerStatus) -> datetime | None:
    state, last_state = status.state, status.last_state
    candidates = (
        state.running if state else None,
        state.terminated if state else None,
        last_state.terminated if last_state else None,
    )
    return next((c.started_at for c in candidates if c is not None and c.started_at is not None), None)
