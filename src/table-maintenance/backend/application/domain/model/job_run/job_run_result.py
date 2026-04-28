"""Define the JobRunResult value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject


@dataclass(frozen=True)
class JobRunResult(ValueObject):
    """Execution result metadata for a completed or failed job run.

    Uses a flexible metadata dict so each runtime/job type can define its own keys.
    """

    duration_ms: int | None
    metadata: dict[str, str]
