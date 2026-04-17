from datetime import UTC, datetime
from unittest.mock import MagicMock

from dependencies.use_cases import get_get_job_run_use_case
from fastapi import FastAPI
from fastapi.testclient import TestClient
from adapter.inbound.web import router
from application.exceptions import JobRunNotFoundError
from application.port.inbound import GetJobRunOutput


def _make_client(use_case: MagicMock) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_get_job_run_use_case] = lambda: use_case
    return TestClient(app)


def test_get_run_returns_200():
    use_case = MagicMock()
    use_case.execute.return_value = GetJobRunOutput(
        run_id="run-1",
        job_id="job-1",
        status="completed",
        started_at=datetime(2026, 4, 4, tzinfo=UTC),
        finished_at=datetime(2026, 4, 4, 1, tzinfo=UTC),
    )
    client = _make_client(use_case)

    resp = client.get("/v1/runs/run-1")
    assert resp.status_code == 200
    assert resp.json()["run_id"] == "run-1"


def test_get_unknown_run_returns_404():
    use_case = MagicMock()
    use_case.execute.side_effect = JobRunNotFoundError("ghost")
    client = _make_client(use_case)

    resp = client.get("/v1/runs/ghost")
    assert resp.status_code == 404
