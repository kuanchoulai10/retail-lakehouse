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


def test_post_job_returns_201():
    repo = MagicMock()
    repo.create.return_value = SAMPLE_JOB
    client = _make_client(repo)

    payload = {
        "job_type": "rewrite_data_files",
        "catalog": "retail",
        "spark_conf": {},
        "rewrite_data_files": {"table": "inventory.orders"},
    }
    response = client.post("/v1/jobs", json=payload)
    assert response.status_code == 201
    assert response.json()["id"] == "abc1234567"
    assert response.json()["status"] == "completed"


def test_post_job_invalid_request_returns_422():
    repo = MagicMock()
    client = _make_client(repo)

    payload = {
        "job_type": "rewrite_data_files",
        "catalog": "retail",
        "spark_conf": {},
    }
    response = client.post("/v1/jobs", json=payload)
    assert response.status_code == 422
