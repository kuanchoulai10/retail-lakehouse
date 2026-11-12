"""Define the JobContainerExit."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JobContainerExit:
    """Describe how one container of a job terminated; ``role`` is ``driver`` or ``executor``."""

    role: str
    reason: str | None
    exit_code: int | None
    message: str | None
