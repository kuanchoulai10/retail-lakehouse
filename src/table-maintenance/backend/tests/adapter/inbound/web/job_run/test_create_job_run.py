"""Tests for create job run endpoint."""

from unittest.mock import MagicMock

from dependencies.use_cases import get_create_job_run_use_case
from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.adapter.inbound.web import router
from core.application.exceptions import JobDisabledError, JobNotFoundError
from core.application.port.inbound.job_run.create_job_run import TriggerJobOutput


def _make_client(use_case: MagicMock) -> TestClient:
    """Provide a test client with the create-job-run use case overridden."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_create_job_run_use_case] = lambda: use_case
    return TestClient(app)


SAMPLE = TriggerJobOutput(job_id="abc1234567")


def test_post_run_returns_202():
    """Return 202 with accepted trigger response."""
    use_case = MagicMock()
    use_case.execute.return_value = SAMPLE
    client = _make_client(use_case)

    resp = client.post("/v1/jobs/abc1234567/runs")
    assert resp.status_code == 202
    assert resp.json() == {"job_id": "abc1234567", "accepted": True}


def test_post_run_disabled_returns_409():
    """Return 409 when the job is disabled."""
    use_case = MagicMock()
    use_case.execute.side_effect = JobDisabledError("abc1234567")
    client = _make_client(use_case)

    resp = client.post("/v1/jobs/abc1234567/runs")
    assert resp.status_code == 409
    assert "abc1234567" in resp.json()["detail"]


def test_post_run_for_missing_job_returns_404():
    """Return 404 when the parent job does not exist."""
    use_case = MagicMock()
    use_case.execute.side_effect = JobNotFoundError("ghost")
    client = _make_client(use_case)

    resp = client.post("/v1/jobs/ghost/runs")
    assert resp.status_code == 404
