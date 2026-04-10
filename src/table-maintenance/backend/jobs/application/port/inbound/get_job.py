from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from base.use_case import UseCase


@dataclass(frozen=True)
class GetJobResult:
    """Application-layer result for GetJob — no domain types leak to the adapter."""

    id: str
    job_type: str
    status: str
    created_at: datetime


class GetJobUseCase(UseCase[str, GetJobResult]):
    """Retrieve a single job by its ID."""
