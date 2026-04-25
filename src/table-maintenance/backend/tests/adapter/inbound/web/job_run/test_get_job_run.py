"""Tests for get job run endpoint."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from api.dependencies.use_cases import get_get_job_run_use_case
from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.adapter.inbound.web import router
from core.application.exceptions import JobRunNotFoundError
from core.application.port.inbound import GetJobRunOutput


def _make_client(use_case: MagicMock) -> TestClient:
    """Provide a test client with the get-job-run use case overridden."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_get_job_run_use_case] = lambda: use_case
    return TestClient(app)


def test_get_run_returns_200():
    """Return 200 with job run details when the run exists."""
    use_case = MagicMock()
    use_case.execute.return_value = GetJobRunOutput(
        run_id="run-1",
        job_id="job-1",
        status="completed",
        trigger_type="manual",
        started_at=datetime(2026, 4, 4, tzinfo=UTC),
        finished_at=datetime(2026, 4, 4, 1, tzinfo=UTC),
    )
    client = _make_client(use_case)

    resp = client.get("/v1/runs/run-1")
    assert resp.status_code == 200
    assert resp.json()["run_id"] == "run-1"
    assert resp.json()["trigger_type"] == "manual"


def test_get_unknown_run_returns_404():
    """Return 404 when the requested job run does not exist."""
    use_case = MagicMock()
    use_case.execute.side_effect = JobRunNotFoundError("ghost")
    client = _make_client(use_case)

    resp = client.get("/v1/runs/ghost")
    assert resp.status_code == 404
