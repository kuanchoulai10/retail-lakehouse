"""Define the FailJobRunOutput dataclass."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class FailJobRunOutput:
    """Output after marking a job run as failed."""

    run_id: str
    status: str
    finished_at: datetime
