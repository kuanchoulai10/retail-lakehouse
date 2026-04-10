from datetime import UTC, datetime
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from jobs.adapter.inbound.web import router
from jobs.adapter.inbound.web.deps import get_repo
from jobs.domain import JobStatus, JobType
from jobs.domain.job import Job
from jobs.domain.job_id import JobId

SAMPLE_JOB = Job(
    id=JobId(value="abc1234567"),
    job_type=JobType.REWRITE_DATA_FILES,
    status=JobStatus.COMPLETED,
    created_at=datetime(2026, 4, 4, tzinfo=UTC),
)


def _make_client(repo: MagicMock) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_repo] = lambda: repo
    return TestClient(app)


def test_list_jobs_returns_200():
    repo = MagicMock()
    repo.list_all.return_value = [SAMPLE_JOB]
    client = _make_client(repo)

    response = client.get("/v1/jobs")
    assert response.status_code == 200
    assert len(response.json()) == 1
