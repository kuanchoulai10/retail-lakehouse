from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class JobApiRequest(BaseModel):
    job_type: str
    catalog: str
    spark_conf: dict[str, str]

    expire_snapshots: dict | None = None
    remove_orphan_files: dict | None = None
    rewrite_data_files: dict | None = None
    rewrite_manifests: dict | None = None

    driver_memory: str = "512m"
    executor_memory: str = "1g"
    executor_instances: int = 1
    cron: str | None = None


class JobApiResponse(BaseModel):
    id: str
    job_type: str
    status: str
    created_at: datetime
