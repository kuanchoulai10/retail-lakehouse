"""Define the FailureEvidence value object."""

from __future__ import annotations

from base import ValueObject
from context.table_maintenance.application.domain.model.table_maintenance_run.attempt_ending import (
    AttemptEnding,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.container_exit import (
    ContainerExit,
)


class FailureEvidence(ValueObject):
    """Hold what is known about a failed maintenance attempt: its ending, error texts and container exits."""

    ended_by: AttemptEnding
    texts: tuple[str, ...] = ()
    containers: tuple[ContainerExit, ...] = ()
