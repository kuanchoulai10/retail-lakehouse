from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, model_validator

from jobs.domain.config.expire_snapshots import ExpireSnapshotsConfig
from jobs.domain.config.remove_orphan_files import RemoveOrphanFilesConfig
from jobs.domain.config.rewrite_data_files import RewriteDataFilesConfig
from jobs.domain.config.rewrite_manifests import RewriteManifestsConfig
from jobs.domain.job_status import JobStatus
from jobs.domain.job_type import JobType


class JobRequest(BaseModel):
    job_type: JobType
    catalog: str
    spark_conf: dict[str, str]

    expire_snapshots: ExpireSnapshotsConfig | None = None
    remove_orphan_files: RemoveOrphanFilesConfig | None = None
    rewrite_data_files: RewriteDataFilesConfig | None = None
    rewrite_manifests: RewriteManifestsConfig | None = None

    driver_memory: str = "512m"
    executor_memory: str = "1g"
    executor_instances: int = 1
    cron: str | None = None

    @model_validator(mode="after")
    def validate_job_config(self) -> JobRequest:
        mapping = {
            JobType.EXPIRE_SNAPSHOTS: self.expire_snapshots,
            JobType.REMOVE_ORPHAN_FILES: self.remove_orphan_files,
            JobType.REWRITE_DATA_FILES: self.rewrite_data_files,
            JobType.REWRITE_MANIFESTS: self.rewrite_manifests,
        }
        if mapping[self.job_type] is None:
            raise ValueError(
                f"Config for job_type={self.job_type.value!r} must be provided (set the '{self.job_type.value}' field)"
            )
        return self


class JobResponse(BaseModel):
    name: str
    kind: str
    namespace: str
    job_type: JobType
    status: JobStatus
    created_at: datetime
