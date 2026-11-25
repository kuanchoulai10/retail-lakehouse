"""Define the RunStatusField annotated type."""

from __future__ import annotations

from typing import Annotated

from pydantic import PlainSerializer, PlainValidator

from context.table_maintenance.application.domain.model.table_maintenance_run.status.run_status import (
    RunStatus,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.status.run_status_factory import (
    RunStatusFactory,
)


def _status_from(value: object) -> RunStatus:
    """Return ``value`` when it is a status, the status of that name when it is a name; refuse anything else."""
    if isinstance(value, RunStatus):
        return value
    if isinstance(value, str):
        return RunStatusFactory.create(value)
    msg = f"a run status is a RunStatus or its name, not {type(value).__name__}"
    raise ValueError(msg)  # noqa: TRY004 - Pydantic turns a ValueError, not a TypeError, into a validation error


def _name_of(status: RunStatus) -> str:
    return status.name.value


# A plain validator, not a before validator: RunStatus is no Pydantic model, so there is no inner schema to hand on to.
RunStatusField = Annotated[RunStatus, PlainValidator(_status_from), PlainSerializer(_name_of, return_type=str)]
"""A model field holding a run's status: it takes a ``RunStatus`` or a name, and dumps the name."""
