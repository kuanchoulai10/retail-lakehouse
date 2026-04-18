from __future__ import annotations

from typing import TYPE_CHECKING

from kubernetes.client.exceptions import ApiException

from adapter.outbound.job_run.k8s.status_mapper import status_from_k8s
from application.domain.model.job import JobId
from application.domain.model.job_run import JobRun, JobRunId, JobRunNotFoundError
from application.port.outbound.job_run.job_runs_repo import BaseJobRunsRepo

if TYPE_CHECKING:
    from kubernetes.client import CustomObjectsApi

    from configs import AppSettings

_GROUP = "sparkoperator.k8s.io"
_VERSION = "v1beta2"
_PLURAL_SPARK = "sparkapplications"
_PLURAL_SCHEDULED = "scheduledsparkapplications"
_JOB_LABEL = "table-maintenance/job-id"


def _to_job_run(resource: dict) -> JobRun:
    meta = resource.get("metadata", {})
    kind = resource.get("kind", "SparkApplication")
    state = resource.get("status", {}).get("applicationState", {}).get("state", "")
    job_id_value = meta.get("labels", {}).get(_JOB_LABEL, meta.get("name", ""))
    return JobRun(
        id=JobRunId(value=meta["name"]),
        job_id=JobId(value=job_id_value),
        status=status_from_k8s(kind, state),
    )


class K8sJobRunsRepo(BaseJobRunsRepo):
    """Read-only view over JobRuns backed by K8s SparkApplication resources."""

    def __init__(self, api: CustomObjectsApi, settings: AppSettings) -> None:
        self._api = api
        self._settings = settings

    def create(self, entity: JobRun) -> JobRun:
        raise NotImplementedError(
            "K8sJobRunsRepo is read-only; runs are created via JobRunExecutor.trigger()"
        )

    def get(self, run_id: JobRunId) -> JobRun:
        for plural in (_PLURAL_SPARK, _PLURAL_SCHEDULED):
            try:
                resource = self._api.get_namespaced_custom_object(
                    group=_GROUP,
                    version=_VERSION,
                    namespace=self._settings.k8s.namespace,
                    plural=plural,
                    name=run_id.value,
                )
                return _to_job_run(resource)
            except ApiException as e:
                if e.status == 404:
                    continue
                raise
        raise JobRunNotFoundError(run_id.value)

    def list_for_job(self, job_id: JobId) -> list[JobRun]:
        selector = f"{_JOB_LABEL}={job_id.value}"
        results: list[JobRun] = []
        for plural in (_PLURAL_SPARK, _PLURAL_SCHEDULED):
            resp = self._api.list_namespaced_custom_object(
                group=_GROUP,
                version=_VERSION,
                namespace=self._settings.k8s.namespace,
                plural=plural,
                label_selector=selector,
            )
            results.extend(_to_job_run(item) for item in resp.get("items", []))
        return results

    def list_all(self) -> list[JobRun]:
        results: list[JobRun] = []
        for plural in (_PLURAL_SPARK, _PLURAL_SCHEDULED):
            resp = self._api.list_namespaced_custom_object(
                group=_GROUP,
                version=_VERSION,
                namespace=self._settings.k8s.namespace,
                plural=plural,
            )
            results.extend(_to_job_run(item) for item in resp.get("items", []))
        return results
