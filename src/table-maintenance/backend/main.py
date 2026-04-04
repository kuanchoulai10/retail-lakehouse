from contextlib import asynccontextmanager

from api.routes.jobs import get_repo
from api.routes.jobs import router as jobs_router
from config import AppSettings
from fastapi import FastAPI
from k8s.client import load_k8s_config
from k8s.jobs_repo import JobsRepository
from kubernetes import client as k8s_client

settings = AppSettings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_k8s_config()
    api = k8s_client.CustomObjectsApi()
    repo = JobsRepository(api, settings)
    app.dependency_overrides[get_repo] = lambda: repo
    yield
    app.dependency_overrides.clear()


app = FastAPI(title="Table Maintenance Backend", lifespan=lifespan)
app.include_router(jobs_router)


@app.get("/health")
def health():
    return {"status": "ok"}
