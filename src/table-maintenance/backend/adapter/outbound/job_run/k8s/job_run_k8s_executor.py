"""Define the JobRunK8sExecutor adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from adapter.outbound.job_run.k8s.constants import (
    GROUP,
    PLURAL_SCHEDULED,
    PLURAL_SPARK,
    VERSION,
)
from adapter.outbound.job_run.k8s.manifest import build_manifest
from application.port.outbound.job_run.job_run_executor import JobRunExecutor

if TYPE_CHECKING:
    from kubernetes.client import CustomObjectsApi

    from adapter.outbound.job_run.k8s.k8s_executor_config import K8sExecutorConfig
    from application.port.outbound.job_run.job_submission import JobSubmission


class JobRunK8sExecutor(JobRunExecutor):
    """Submit a job by creating a SparkApplication (or ScheduledSparkApplication) in K8s."""

    def __init__(self, api: CustomObjectsApi, config: K8sExecutorConfig) -> None:
        """Initialize with a Kubernetes API client and executor config."""
        self._api = api
        self._config = config

    def submit(self, submission: JobSubmission) -> None:
        """Create a SparkApplication in Kubernetes."""
        manifest = build_manifest(submission, self._config)
        plural = PLURAL_SCHEDULED if submission.cron_expression else PLURAL_SPARK
        self._api.create_namespaced_custom_object(
            group=GROUP,
            version=VERSION,
            namespace=self._config.namespace,
            plural=plural,
            body=manifest,
        )
