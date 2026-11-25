"""Define the ContainerExit value object."""

from __future__ import annotations

from base import ValueObject


class ContainerExit(ValueObject):
    """Describe how one container of a maintenance attempt's job terminated."""

    role: str
    reason: str | None = None
    exit_code: int | None = None
    message: str | None = None
