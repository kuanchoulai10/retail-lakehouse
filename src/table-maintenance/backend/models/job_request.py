from __future__ import annotations

from configs import JobType
from configs.jobs.expire_snapshots import ExpireSnapshotsConfig
from configs.jobs.remove_orphan_files import RemoveOrphanFilesConfig
from configs.jobs.rewrite_data_files import RewriteDataFilesConfig
from configs.jobs.rewrite_manifests import RewriteManifestsConfig
from pydantic import BaseModel, model_validator


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
