"""Define the MetricsProperties value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject


@dataclass(frozen=True)
class MetricsProperties(ValueObject):
    """Write metrics configuration properties."""

    default_mode: str | None = None
