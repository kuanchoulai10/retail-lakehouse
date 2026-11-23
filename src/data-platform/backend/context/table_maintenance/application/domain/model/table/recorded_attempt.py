"""Define the RecordedAttempt value object."""

from __future__ import annotations

from pydantic import PositiveInt

from base import ValueObject
from context.table_maintenance.application.domain.model.shared import TableMaintenanceRunId


class RecordedAttempt(ValueObject):
    """One attempt of one maintenance run whose result a table has taken in."""

    run_id: TableMaintenanceRunId
    attempt: PositiveInt
