"""Define the PositiveDuration type."""

from __future__ import annotations

from datetime import timedelta
from typing import Annotated

from pydantic import AfterValidator

from base.model import WholeSeconds


def _positive(value: timedelta) -> timedelta:
    if value <= timedelta(0):
        raise ValueError("must be positive")
    return value


PositiveDuration = Annotated[WholeSeconds, AfterValidator(_positive)]
"""A ``WholeSeconds`` duration longer than zero."""
