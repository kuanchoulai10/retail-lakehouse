"""Define the SplitProperties value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject


@dataclass(frozen=True)
class SplitProperties(ValueObject):
    """Read split planning properties."""

    size: int | None = None
    lookback: int | None = None
    open_file_cost: int | None = None
