from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from jobs.adapter.inbound.web import router as jobs_router
from kubernetes import client as k8s_client
from shared.k8s.client import load_k8s_config


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_k8s_config()
    app.state.k8s_api = k8s_client.CustomObjectsApi()
    yield


app = FastAPI(title="Table Maintenance Backend", lifespan=lifespan)
app.include_router(jobs_router)


@app.get("/health")
def health():
    return {"status": "ok"}
