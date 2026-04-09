from datetime import UTC, datetime
from unittest.mock import MagicMock

from api.jobs import router
from api.jobs._deps import get_repo
from configs.base import JobType
from fastapi import FastAPI
from fastapi.testclient import TestClient
from models.job_response import JobResponse
from models.job_status import JobStatus

SAMPLE_RESPONSE = JobResponse(
    name="table-maintenance-rewrite-data-files-abc123",
    kind="SparkApplication",
    namespace="default",
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
    repo.create.return_value = SAMPLE_RESPONSE
    client = _make_client(repo)

    payload = {
        "job_type": "rewrite_data_files",
        "catalog": "retail",
        "spark_conf": {},
        "rewrite_data_files": {"table": "inventory.orders"},
    }
    response = client.post("/v1/jobs", json=payload)
    assert response.status_code == 201
    assert response.json()["name"] == "table-maintenance-rewrite-data-files-abc123"
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
