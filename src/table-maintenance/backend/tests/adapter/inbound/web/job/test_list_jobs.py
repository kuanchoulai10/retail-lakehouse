"""Tests for list jobs endpoint."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from dependencies.use_cases import get_list_jobs_use_case
from fastapi import FastAPI
from fastapi.testclient import TestClient
from adapter.inbound.web import router
from application.port.inbound import ListJobsOutput, ListJobsOutputItem


def _make_client(use_case: MagicMock) -> TestClient:
    """Provide a test client with the list-jobs use case overridden."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_list_jobs_use_case] = lambda: use_case
    return TestClient(app)


SAMPLE_OUTPUT = ListJobsOutput(
    jobs=[
        ListJobsOutputItem(
            id="abc1234567",
            job_type="rewrite_data_files",
            status="paused",
            created_at=datetime(2026, 4, 4, tzinfo=UTC),
            updated_at=datetime(2026, 4, 4, tzinfo=UTC),
        ),
    ],
)


def test_list_jobs_returns_200():
    """Return 200 with a list of jobs."""
    use_case = MagicMock()
    use_case.execute.return_value = SAMPLE_OUTPUT
    client = _make_client(use_case)

    response = client.get("/v1/jobs")
    assert response.status_code == 200
    assert len(response.json()) == 1
    body = response.json()[0]
    assert body["id"] == "abc1234567"
    assert body["status"] == "paused"
