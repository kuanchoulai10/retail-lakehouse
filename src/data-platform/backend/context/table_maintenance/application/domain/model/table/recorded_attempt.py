"""Define the RecordedAttempt value object."""

from __future__ import annotations

from pydantic import PositiveInt, field_validator

from base import ValueObject
from shared_kernel import prefixed_id_pattern

_RUN_ID = prefixed_id_pattern("mr")


class RecordedAttempt(ValueObject):
    """One attempt of one maintenance run whose result a table has taken in.

    ``run_id`` is checked against the same ``mr-`` shape as ``TableMaintenanceRunId``. It stays a
    string because the run aggregate's package imports this one (for ``TableId``), so typing it
    as the run id would make the two packages import each other.
    """

    run_id: str
    attempt: PositiveInt

    @field_validator("run_id")
    @classmethod
    def _is_a_run_id(cls, value: str) -> str:
        if _RUN_ID.fullmatch(value) is None:
            raise ValueError("TableMaintenanceRunId must look like mr-<26 base32 characters>")
        return value
