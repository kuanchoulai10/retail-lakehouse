"""Define the NonNegativeDuration type."""

from __future__ import annotations

from datetime import timedelta
from typing import Annotated

from pydantic import AfterValidator

from base import WholeSeconds


def _non_negative(value: timedelta) -> timedelta:
    if value < timedelta(0):
        raise ValueError("must not be negative")
    return value


NonNegativeDuration = Annotated[WholeSeconds, AfterValidator(_non_negative)]
"""A ``WholeSeconds`` duration of zero or longer."""
