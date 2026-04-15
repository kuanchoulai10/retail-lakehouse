from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends
from adapter.outbound.k8s.k8s_jobs_repo import K8sJobsRepo

from dependencies.k8s import get_k8s_api
from dependencies.settings import get_settings

if TYPE_CHECKING:
    from application.port.outbound.jobs_repo import BaseJobsRepo
    from kubernetes.client import CustomObjectsApi
    from configs import AppSettings


def get_jobs_repo(
    api: CustomObjectsApi = Depends(get_k8s_api),
    settings: AppSettings = Depends(get_settings),
) -> BaseJobsRepo:
    return K8sJobsRepo(api, settings)
