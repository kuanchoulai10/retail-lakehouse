"""Define the PeakHeapUse value object."""

from __future__ import annotations

from pydantic import NonNegativeInt

from base import ValueObject


class PeakHeapUse(ValueObject):
    """The most JVM heap a maintenance job's driver and busiest executor used, in bytes; None when not measured."""

    driver_bytes: NonNegativeInt | None = None
    executor_bytes: NonNegativeInt | None = None
