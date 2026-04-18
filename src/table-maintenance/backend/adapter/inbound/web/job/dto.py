"""Define Job API request and response DTOs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class JobApiRequest(BaseModel):
    """Request body for creating a new job."""

    job_type: str
    catalog: str

    expire_snapshots: dict | None = None
    remove_orphan_files: dict | None = None
    rewrite_data_files: dict | None = None
    rewrite_manifests: dict | None = None

    cron: str | None = None
    enabled: bool = False


class UpdateJobApiRequest(BaseModel):
    """Partial update — only fields present are applied."""

    enabled: bool | None = None
    catalog: str | None = None
    cron: str | None = None
    job_config: dict | None = None


class JobApiResponse(BaseModel):
    """Response body representing a job."""

    id: str
    job_type: str
    enabled: bool
    created_at: datetime
    updated_at: datetime
