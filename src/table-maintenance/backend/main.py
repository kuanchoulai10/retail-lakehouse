from contextlib import asynccontextmanager

from api.jobs import router as jobs_router
from api.jobs._deps import get_repo
from configs.app import AppSettings
from fastapi import FastAPI
from k8s.client import load_k8s_config
from kubernetes import client as k8s_client
from repos.k8s import K8sJobsRepo

settings = AppSettings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_k8s_config()
    api = k8s_client.CustomObjectsApi()
    repo = K8sJobsRepo(api, settings)
    app.dependency_overrides[get_repo] = lambda: repo
    yield
    app.dependency_overrides.clear()


app = FastAPI(title="Table Maintenance Backend", lifespan=lifespan)
app.include_router(jobs_router)


@app.get("/health")
def health():
    return {"status": "ok"}
