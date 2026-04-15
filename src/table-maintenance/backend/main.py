from __future__ import annotations

from fastapi import FastAPI
from adapter.inbound.web import router as jobs_router

app = FastAPI(title="Table Maintenance Backend")
app.include_router(jobs_router)


@app.get("/health")
def health():
    return {"status": "ok"}
