from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from kubernetes.client.exceptions import ApiException

from jobs.adapter.outbound.k8s.manifest import build_manifest
from jobs.adapter.outbound.k8s.status_mapper import status_from_k8s
from jobs.application.domain.model.exceptions import JobNotFoundError
from jobs.application.domain.model.job import Job
from jobs.application.domain.model.job_id import JobId
from jobs.application.domain.model.job_type import JobType
from jobs.application.port.outbound.jobs_repo import BaseJobsRepo

if TYPE_CHECKING:
    from kubernetes.client import CustomObjectsApi
    from shared.configs import AppSettings

    from jobs.adapter.inbound.web.dto import JobApiRequest as JobRequest

_GROUP = "sparkoperator.k8s.io"
_VERSION = "v1beta2"
_PLURAL_SPARK = "sparkapplications"
_PLURAL_SCHEDULED = "scheduledsparkapplications"


def _generate_name(job_type: str | JobType) -> str:
    value = job_type.value if isinstance(job_type, JobType) else job_type
    slug = value.replace("_", "-")
    return f"table-maintenance-{slug}-{secrets.token_hex(5)}"


def _extract_job_type(resource: dict) -> JobType:
    for env in resource.get("spec", {}).get("driver", {}).get("env", []):
        if env["name"] == "GLAC_JOB_TYPE":
            return JobType(env["value"])
    for env in resource.get("spec", {}).get("template", {}).get("driver", {}).get("env", []):
        if env["name"] == "GLAC_JOB_TYPE":
            return JobType(env["value"])
    raise ValueError(f"Cannot determine job_type from resource {resource.get('metadata', {}).get('name')}")


def _to_job(resource: dict, job_type: JobType) -> Job:
    meta = resource.get("metadata", {})
    ts = meta.get("creationTimestamp")
    created_at = datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else datetime.now(UTC)
    kind = resource.get("kind", "SparkApplication")
    state = resource.get("status", {}).get("applicationState", {}).get("state", "")
    return Job(
        id=JobId(value=meta["name"]),
        job_type=job_type,
        status=status_from_k8s(kind, state),
        created_at=created_at,
    )


class K8sJobsRepo(BaseJobsRepo):
    def __init__(self, api: CustomObjectsApi, settings: AppSettings):
        self._api = api
        self._settings = settings

    def create(self, request: JobRequest) -> Job:
        name = _generate_name(request.job_type)
        manifest = build_manifest(name, request, self._settings)
        plural = _PLURAL_SCHEDULED if manifest["kind"] == "ScheduledSparkApplication" else _PLURAL_SPARK
        resource = self._api.create_namespaced_custom_object(
            group=_GROUP,
            version=_VERSION,
            namespace=self._settings.namespace,
            plural=plural,
            body=manifest,
        )
        return _to_job(resource, JobType(request.job_type))

    def list_all(self) -> list[Job]:
        results = []
        for plural in (_PLURAL_SPARK, _PLURAL_SCHEDULED):
            resp = self._api.list_namespaced_custom_object(
                group=_GROUP,
                version=_VERSION,
                namespace=self._settings.namespace,
                plural=plural,
            )
            for item in resp.get("items", []):
                try:
                    results.append(_to_job(item, _extract_job_type(item)))
                except ValueError:
                    continue
        return results

    def get(self, name: str) -> Job:
        for plural in (_PLURAL_SPARK, _PLURAL_SCHEDULED):
            try:
                resource = self._api.get_namespaced_custom_object(
                    group=_GROUP,
                    version=_VERSION,
                    namespace=self._settings.namespace,
                    plural=plural,
                    name=name,
                )
                return _to_job(resource, _extract_job_type(resource))
            except ApiException as e:
                if e.status == 404:
                    continue
                raise
        raise JobNotFoundError(name)

    def delete(self, name: str) -> None:
        for plural in (_PLURAL_SPARK, _PLURAL_SCHEDULED):
            try:
                self._api.delete_namespaced_custom_object(
                    group=_GROUP,
                    version=_VERSION,
                    namespace=self._settings.namespace,
                    plural=plural,
                    name=name,
                )
                return
            except ApiException as e:
                if e.status == 404:
                    continue
                raise
        raise JobNotFoundError(name)
