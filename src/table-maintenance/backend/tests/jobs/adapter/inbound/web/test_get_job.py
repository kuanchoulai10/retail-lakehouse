from datetime import UTC, datetime
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from jobs.adapter.inbound.web import router
from jobs.adapter.inbound.web.get_job import _get_use_case
from jobs.application.service.get_job import GetJobService
from jobs.domain import JobNotFoundError, JobStatus, JobType
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
    app.dependency_overrides[_get_use_case] = lambda: GetJobService(repo)
    return TestClient(app)


def test_get_job_returns_200():
    repo = MagicMock()
    repo.get.return_value = SAMPLE_JOB
    client = _make_client(repo)

    response = client.get("/v1/jobs/abc1234567")
    assert response.status_code == 200
    assert response.json()["id"] == "abc1234567"


def test_get_job_not_found_returns_404():
    repo = MagicMock()
    repo.get.side_effect = JobNotFoundError("nonexistent")
    client = _make_client(repo)

    response = client.get("/v1/jobs/nonexistent")
    assert response.status_code == 404
    assert "nonexistent" in response.json()["detail"]
