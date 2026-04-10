from datetime import UTC, datetime
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from jobs.adapter.inbound.web import router
from jobs.adapter.inbound.web.get_job import _get_use_case
from jobs.application.exceptions import JobNotFoundError
from jobs.application.port.inbound.get_job import GetJobResult


def _make_client(use_case: MagicMock) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[_get_use_case] = lambda: use_case
    return TestClient(app)


SAMPLE_RESULT = GetJobResult(
    id="abc1234567",
    job_type="rewrite_data_files",
    status="completed",
    created_at=datetime(2026, 4, 4, tzinfo=UTC),
)


def test_get_job_returns_200():
    use_case = MagicMock()
    use_case.execute.return_value = SAMPLE_RESULT
    client = _make_client(use_case)

    response = client.get("/v1/jobs/abc1234567")
    assert response.status_code == 200
    assert response.json()["id"] == "abc1234567"
    assert response.json()["job_type"] == "rewrite_data_files"


def test_get_job_not_found_returns_404():
    use_case = MagicMock()
    use_case.execute.side_effect = JobNotFoundError("nonexistent")
    client = _make_client(use_case)

    response = client.get("/v1/jobs/nonexistent")
    assert response.status_code == 404
    assert "nonexistent" in response.json()["detail"]
