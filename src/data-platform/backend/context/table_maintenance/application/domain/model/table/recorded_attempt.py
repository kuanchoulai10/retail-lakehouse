"""Define the RecordedAttempt value object."""

from __future__ import annotations

from pydantic import Field, PositiveInt

from base import ValueObject


class RecordedAttempt(ValueObject):
    """One attempt of one maintenance run whose result a table has taken in."""

    run_id: str = Field(min_length=1)
    attempt: PositiveInt
