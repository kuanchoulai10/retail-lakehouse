"""Define the UpdateJobInput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UpdateJobInput:
    """Partial update: only non-None fields are applied."""

    job_id: str
    enabled: bool | None = None
    catalog: str | None = None
    cron: str | None = None
    job_config: dict | None = None
