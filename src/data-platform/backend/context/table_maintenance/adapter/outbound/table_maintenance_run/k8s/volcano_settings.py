"""Define the VolcanoSettings."""

from __future__ import annotations

from dataclasses import dataclass

URGENT_PRIORITY = "P0"


@dataclass(frozen=True)
class VolcanoSettings:
    """Name the Volcano queues and priority classes a maintenance job is scheduled in.

    A P0 job goes to ``urgent_queue``; every other priority goes to ``queue``. The
    priority class is ``priority_class_prefix``, a dash and the lowercase priority.
    """

    queue: str = "table-maintenance"
    urgent_queue: str = "table-maintenance-urgent"
    priority_class_prefix: str = "table-maintenance"

    def queue_for(self, priority: str) -> str:
        """Return the queue a job of ``priority`` goes to."""
        return self.urgent_queue if priority == URGENT_PRIORITY else self.queue

    def priority_class_for(self, priority: str) -> str:
        """Return the priority class of a job of ``priority``."""
        return f"{self.priority_class_prefix}-{priority.lower()}"
