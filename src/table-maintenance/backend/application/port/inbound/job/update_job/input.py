"""Define the UpdateJobUseCaseInput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UpdateJobUseCaseInput:
    """Partial update: only non-None fields are applied."""

    job_id: str
    status: str | None = None
    catalog: str | None = None
    cron: str | None = None
    job_config: dict | None = None
