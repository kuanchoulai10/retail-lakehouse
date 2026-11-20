"""Define the AtMost value object."""

from __future__ import annotations

from pydantic import NonNegativeInt

from base import ValueObject


class AtMost(ValueObject):
    """A target: the table is on target while the measured count stays at or under ``at_most``."""

    at_most: NonNegativeInt
