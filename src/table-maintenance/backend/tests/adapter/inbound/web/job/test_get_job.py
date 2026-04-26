"""Tests for get job endpoint."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from bootstrap.dependencies.use_cases import get_get_job_use_case
from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.adapter.inbound.web import router
from application.exceptions import JobNotFoundError
from application.port.inbound import GetJobOutput


def _make_client(use_case: MagicMock) -> TestClient:
    """Provide a test client with the get-job use case overridden."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_get_job_use_case] = lambda: use_case
    return TestClient(app)


SAMPLE_RESULT = GetJobOutput(
    id="abc1234567",
    job_type="rewrite_data_files",
    status="active",
    created_at=datetime(2026, 4, 4, tzinfo=UTC),
    updated_at=datetime(2026, 4, 4, tzinfo=UTC),
)


def test_get_job_returns_200():
    """Return 200 with job details when the job exists."""
    use_case = MagicMock()
    use_case.execute.return_value = SAMPLE_RESULT
    client = _make_client(use_case)

    response = client.get("/v1/jobs/abc1234567")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "abc1234567"
    assert body["job_type"] == "rewrite_data_files"
    assert body["status"] == "active"


def test_get_job_not_found_returns_404():
    """Return 404 when the requested job does not exist."""
    use_case = MagicMock()
    use_case.execute.side_effect = JobNotFoundError("nonexistent")
    client = _make_client(use_case)

    response = client.get("/v1/jobs/nonexistent")
    assert response.status_code == 404
    assert "nonexistent" in response.json()["detail"]
