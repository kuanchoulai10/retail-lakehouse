"""Define the SizeMemory value object."""

from __future__ import annotations

from pydantic import PositiveInt

from base import ValueObject


class SizeMemory(ValueObject):
    """The JVM heap one compute size gives its driver and each executor, in bytes."""

    driver_bytes: PositiveInt
    executor_bytes: PositiveInt
