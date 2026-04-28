"""Define the CompleteJobRunOutput dataclass."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class CompleteJobRunOutput:
    """Output after completing a job run."""

    run_id: str
    status: str
    finished_at: datetime
