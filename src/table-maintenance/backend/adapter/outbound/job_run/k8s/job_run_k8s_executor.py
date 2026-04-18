from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from adapter.outbound.job_run.k8s.manifest import build_manifest
from application.domain.model.job_run import JobRun, JobRunId, JobRunStatus
from application.port.outbound.job_run.job_run_executor import JobRunExecutor

if TYPE_CHECKING:
    from kubernetes.client import CustomObjectsApi

    from application.domain.model.job import Job
    from configs import AppSettings

_GROUP = "sparkoperator.k8s.io"
_VERSION = "v1beta2"
_PLURAL_SPARK = "sparkapplications"
_PLURAL_SCHEDULED = "scheduledsparkapplications"


class JobRunK8sExecutor(JobRunExecutor):
    """Triggers a JobRun by creating a SparkApplication (or ScheduledSparkApplication) in K8s."""

    def __init__(self, api: CustomObjectsApi, settings: AppSettings) -> None:
        self._api = api
        self._settings = settings

    def trigger(self, job: Job) -> JobRun:
        if job.cron:
            run_id = JobRunId(value=job.id.value)
            plural = _PLURAL_SCHEDULED
        else:
            run_id = JobRunId(value=f"{job.id.value}-{secrets.token_hex(3)}")
            plural = _PLURAL_SPARK

        manifest = build_manifest(job, run_id.value, self._settings)
        self._api.create_namespaced_custom_object(
            group=_GROUP,
            version=_VERSION,
            namespace=self._settings.k8s.namespace,
            plural=plural,
            body=manifest,
        )
        return JobRun(
            id=run_id,
            job_id=job.id,
            status=JobRunStatus.PENDING,
            started_at=datetime.now(UTC),
        )
