"""Define the TemporalSettings configuration model."""

from __future__ import annotations

from pydantic import BaseModel


class TemporalSettings(BaseModel):
    """Temporal frontend address, namespace and task queue."""

    address: str = "temporal-frontend.temporal.svc.cluster.local:7233"
    namespace: str = "default"
    task_queue: str = "table-maintenance"
