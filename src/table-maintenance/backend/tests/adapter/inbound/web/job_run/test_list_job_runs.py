"""Tests for list job runs endpoint."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from bootstrap.dependencies.use_cases import get_list_job_runs_use_case
from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.adapter.inbound.web import router
from application.port.inbound import ListJobRunsOutput, ListJobRunsOutputItem


def _make_client(use_case: MagicMock) -> TestClient:
    """Provide a test client with the list-job-runs use case overridden."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_list_job_runs_use_case] = lambda: use_case
    return TestClient(app)


def test_list_job_runs_returns_200():
    """Return 200 with a list of job runs for the given job."""
    use_case = MagicMock()
    use_case.execute.return_value = ListJobRunsOutput(
        runs=[
            ListJobRunsOutputItem(
                run_id="a-1",
                job_id="a",
                status="running",
                trigger_type="manual",
                started_at=datetime(2026, 4, 4, tzinfo=UTC),
                finished_at=None,
            ),
        ],
    )
    client = _make_client(use_case)

    resp = client.get("/v1/jobs/a/runs")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["run_id"] == "a-1"
