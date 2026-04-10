from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from api import jobs_router
from api.jobs._deps import get_repo
from configs import AppSettings
from fastapi import FastAPI
from k8s.client import load_k8s_config
from kubernetes import client as k8s_client
from repos import K8sJobsRepo

if TYPE_CHECKING:
    from repos import BaseJobsRepo

settings = AppSettings()


def create_repo(settings: AppSettings) -> BaseJobsRepo:
    load_k8s_config()
    api = k8s_client.CustomObjectsApi()
    return K8sJobsRepo(api, settings)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.repo = create_repo(settings)
    app.dependency_overrides[get_repo] = lambda: app.state.repo
    yield
    app.dependency_overrides.clear()


app = FastAPI(title="Table Maintenance Backend", lifespan=lifespan)
app.include_router(jobs_router)


@app.get("/health")
def health():
    return {"status": "ok"}
