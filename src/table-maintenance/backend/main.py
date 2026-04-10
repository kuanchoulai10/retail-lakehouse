from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from jobs.adapter.inbound.web import router as jobs_router
from jobs.adapter.inbound.web.deps import get_repo
from jobs.adapter.inbound.web.get_job import _get_use_case as get_job_dep
from jobs.adapter.outbound.k8s.k8s_jobs_repo import K8sJobsRepo
from jobs.application.service.get_job import GetJobService
from kubernetes import client as k8s_client
from shared.configs import AppSettings
from shared.k8s.client import load_k8s_config

if TYPE_CHECKING:
    from jobs.application.port.outbound.jobs_repo import BaseJobsRepo

settings = AppSettings()


def create_repo(settings: AppSettings) -> BaseJobsRepo:
    load_k8s_config()
    api = k8s_client.CustomObjectsApi()
    return K8sJobsRepo(api, settings)


@asynccontextmanager
async def lifespan(app: FastAPI):
    repo = create_repo(settings)
    app.state.repo = repo
    app.dependency_overrides[get_repo] = lambda: repo
    app.dependency_overrides[get_job_dep] = lambda: GetJobService(repo)
    yield
    app.dependency_overrides.clear()


app = FastAPI(title="Table Maintenance Backend", lifespan=lifespan)
app.include_router(jobs_router)


@app.get("/health")
def health():
    return {"status": "ok"}
