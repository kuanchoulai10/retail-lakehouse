"""Define the VolcanoSettings."""

from __future__ import annotations

from dataclasses import dataclass

from context.table_maintenance.application.port.outbound.table_maintenance_run import TablePriority


@dataclass(frozen=True)
class VolcanoSettings:
    """Name the Volcano queues and priority classes a maintenance job is scheduled in.

    A P0 job goes to ``urgent_queue``; every other priority goes to ``queue``. The
    priority class is ``priority_class_prefix``, a dash and the lowercase priority.
    A priority other than exactly P0, P1, P2 or P3 is refused with ``ValueError``.
    """

    queue: str = "table-maintenance"
    urgent_queue: str = "table-maintenance-urgent"
    priority_class_prefix: str = "table-maintenance"

    def queue_for(self, priority: str) -> str:
        """Return the queue a job of ``priority`` goes to."""
        return self.urgent_queue if _known(priority) is TablePriority.P0 else self.queue

    def priority_class_for(self, priority: str) -> str:
        """Return the priority class of a job of ``priority``."""
        return f"{self.priority_class_prefix}-{_known(priority).value.lower()}"


def _known(priority: str) -> TablePriority:
    try:
        return TablePriority(priority)
    except ValueError as exc:
        msg = f"unknown priority {priority!r}; known priorities: {', '.join(TablePriority)}"
        raise ValueError(msg) from exc
