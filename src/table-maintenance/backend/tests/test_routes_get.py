from datetime import UTC, datetime
from unittest.mock import MagicMock

from api.routes import router
from api.routes._deps import get_repo
from configs.base import JobType
from fastapi import FastAPI
from fastapi.testclient import TestClient
from models.responses import JobResponse, JobStatus
from repos.base import JobNotFoundError

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

    response = client.get("/jobs/table-maintenance-rewrite-data-files-abc123")
    assert response.status_code == 200
    assert response.json()["kind"] == "SparkApplication"


def test_get_job_not_found_returns_404():
    repo = MagicMock()
    repo.get.side_effect = JobNotFoundError("nonexistent")
    client = _make_client(repo)

    response = client.get("/jobs/nonexistent")
    assert response.status_code == 404
    assert "nonexistent" in response.json()["detail"]
