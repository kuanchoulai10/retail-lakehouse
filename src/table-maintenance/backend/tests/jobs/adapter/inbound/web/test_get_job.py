from datetime import UTC, datetime
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from jobs.adapter.inbound.web import router
from jobs.adapter.inbound.web.deps import get_repo
from jobs.adapter.inbound.web.dto import JobResponse
from jobs.domain import JobNotFoundError, JobStatus, JobType

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


def test_get_job_returns_200():
    repo = MagicMock()
    repo.get.return_value = SAMPLE_RESPONSE
    client = _make_client(repo)

    response = client.get("/v1/jobs/table-maintenance-rewrite-data-files-abc123")
    assert response.status_code == 200
    assert response.json()["kind"] == "SparkApplication"


def test_get_job_not_found_returns_404():
    repo = MagicMock()
    repo.get.side_effect = JobNotFoundError("nonexistent")
    client = _make_client(repo)

    response = client.get("/v1/jobs/nonexistent")
    assert response.status_code == 404
    assert "nonexistent" in response.json()["detail"]
