from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from configs.base import JobType
from k8s.manifest import build_manifest
from kubernetes.client.exceptions import ApiException
from models.responses import JobResponse, status_from_k8s

from repos.base import JobNotFoundError, JobsRepo

if TYPE_CHECKING:
    from config import AppSettings
    from kubernetes.client import CustomObjectsApi
    from models.requests import JobRequest

_GROUP = "sparkoperator.k8s.io"
_VERSION = "v1beta2"
_PLURAL_SPARK = "sparkapplications"
_PLURAL_SCHEDULED = "scheduledsparkapplications"


def _generate_name(job_type: JobType) -> str:
    suffix = uuid.uuid4().hex[:8]
    return f"table-maintenance-{job_type.value.replace('_', '-')}-{suffix}"


def _extract_job_type(resource: dict) -> JobType:
    for env in resource.get("spec", {}).get("driver", {}).get("env", []):
        if env["name"] == "GLAC_JOB_TYPE":
            return JobType(env["value"])
    for env in resource.get("spec", {}).get("template", {}).get("driver", {}).get("env", []):
        if env["name"] == "GLAC_JOB_TYPE":
            return JobType(env["value"])
    raise ValueError(f"Cannot determine job_type from resource {resource.get('metadata', {}).get('name')}")


def _to_response(resource: dict, job_type: JobType) -> JobResponse:
    meta = resource.get("metadata", {})
    ts = meta.get("creationTimestamp")
    created_at = datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else datetime.now(UTC)
    kind = resource.get("kind", "SparkApplication")
    state = resource.get("status", {}).get("applicationState", {}).get("state", "")
    return JobResponse(
        name=meta["name"],
        kind=kind,
        namespace=meta.get("namespace", "default"),
        job_type=job_type,
        status=status_from_k8s(kind, state),
        created_at=created_at,
    )


class K8sJobsRepo(JobsRepo):
    def __init__(self, api: CustomObjectsApi, settings: AppSettings):
        self._api = api
        self._settings = settings

    def create(self, request: JobRequest) -> JobResponse:
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
        return _to_response(resource, request.job_type)

    def list_all(self) -> list[JobResponse]:
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
                    results.append(_to_response(item, _extract_job_type(item)))
                except ValueError:
                    continue
        return results

    def get(self, name: str) -> JobResponse:
        for plural in (_PLURAL_SPARK, _PLURAL_SCHEDULED):
            try:
                resource = self._api.get_namespaced_custom_object(
                    group=_GROUP,
                    version=_VERSION,
                    namespace=self._settings.namespace,
                    plural=plural,
                    name=name,
                )
                return _to_response(resource, _extract_job_type(resource))
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
