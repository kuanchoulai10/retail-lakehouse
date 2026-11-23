"""Define the PeakMemoryUse value object."""

from __future__ import annotations

from pydantic import NonNegativeInt

from base import ValueObject


class PeakMemoryUse(ValueObject):
    """The most JVM heap a maintenance job's coordinator and busiest worker used, in bytes; None when not measured."""

    coordinator_bytes: NonNegativeInt | None = None
    worker_bytes: NonNegativeInt | None = None
