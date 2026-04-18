from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from adapter.inbound.web import router as jobs_router
from adapter.outbound.sql.metadata import metadata
from configs import JobsRepoAdapter, JobRunsRepoAdapter
from dependencies.repos import _cached_sql_engine
from dependencies.settings import get_settings

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    uses_sql = (
        settings.jobs_repo_adapter == JobsRepoAdapter.SQL
        or settings.job_runs_repo_adapter == JobRunsRepoAdapter.SQL
    )
    if uses_sql:
        engine = _cached_sql_engine(settings)
        metadata.create_all(engine)
    yield


app = FastAPI(title="Table Maintenance Backend", lifespan=lifespan)
app.include_router(jobs_router)


@app.get("/health")
def health():
    return {"status": "ok"}
