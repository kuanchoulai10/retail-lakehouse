"""Define the SizeMemory value object."""

from __future__ import annotations

from pydantic import PositiveInt

from base import ValueObject


class SizeMemory(ValueObject):
    """The JVM heap one compute size gives its coordinator and each worker, in bytes."""

    coordinator_bytes: PositiveInt
    worker_bytes: PositiveInt
