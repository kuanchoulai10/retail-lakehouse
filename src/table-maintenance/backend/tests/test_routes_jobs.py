from datetime import UTC, datetime
from unittest.mock import MagicMock

from api.routes.jobs import get_repo, router
from configs.base import JobType
from fastapi import FastAPI
from fastapi.testclient import TestClient
from models.responses import JobResponse, JobStatus

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
    response = client.post("/jobs", json=payload)
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
        # missing rewrite_data_files config
    }
    response = client.post("/jobs", json=payload)
    assert response.status_code == 422


def test_list_jobs_returns_200():
    repo = MagicMock()
    repo.list_all.return_value = [SAMPLE_RESPONSE]
    client = _make_client(repo)

    response = client.get("/jobs")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_job_returns_200():
    repo = MagicMock()
    repo.get.return_value = SAMPLE_RESPONSE
    client = _make_client(repo)

    response = client.get("/jobs/table-maintenance-rewrite-data-files-abc123")
    assert response.status_code == 200
    assert response.json()["kind"] == "SparkApplication"


def test_get_job_not_found_returns_404():
    from fastapi import HTTPException

    repo = MagicMock()
    repo.get.side_effect = HTTPException(status_code=404, detail="Job not found")
    client = _make_client(repo)

    response = client.get("/jobs/nonexistent")
    assert response.status_code == 404


def test_delete_job_returns_204():
    repo = MagicMock()
    repo.delete.return_value = None
    client = _make_client(repo)

    response = client.delete("/jobs/table-maintenance-rewrite-data-files-abc123")
    assert response.status_code == 204


def test_delete_job_not_found_returns_404():
    from fastapi import HTTPException

    repo = MagicMock()
    repo.delete.side_effect = HTTPException(status_code=404, detail="Job not found")
    client = _make_client(repo)

    response = client.delete("/jobs/nonexistent")
    assert response.status_code == 404
