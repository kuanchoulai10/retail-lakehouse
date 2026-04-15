from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class JobApiRequest(BaseModel):
    job_type: str
    catalog: str

    expire_snapshots: dict | None = None
    remove_orphan_files: dict | None = None
    rewrite_data_files: dict | None = None
    rewrite_manifests: dict | None = None

    cron: str | None = None


class JobApiResponse(BaseModel):
    id: str
    job_type: str
    status: str
    created_at: datetime
