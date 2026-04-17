from datetime import UTC, datetime
from unittest.mock import MagicMock

from dependencies.use_cases import get_update_job_use_case
from fastapi import FastAPI
from fastapi.testclient import TestClient
from adapter.inbound.web import router
from application.exceptions import JobNotFoundError
from application.port.inbound import UpdateJobOutput


def _make_client(use_case: MagicMock) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_update_job_use_case] = lambda: use_case
    return TestClient(app)


SAMPLE = UpdateJobOutput(
    id="abc1234567",
    job_type="rewrite_data_files",
    enabled=True,
    created_at=datetime(2026, 4, 4, tzinfo=UTC),
    updated_at=datetime(2026, 4, 5, tzinfo=UTC),
)


def test_patch_job_returns_200():
    use_case = MagicMock()
    use_case.execute.return_value = SAMPLE
    client = _make_client(use_case)

    resp = client.patch("/v1/jobs/abc1234567", json={"enabled": True})
    assert resp.status_code == 200
    assert resp.json()["enabled"] is True


def test_patch_unknown_job_returns_404():
    use_case = MagicMock()
    use_case.execute.side_effect = JobNotFoundError("ghost")
    client = _make_client(use_case)

    resp = client.patch("/v1/jobs/ghost", json={"enabled": True})
    assert resp.status_code == 404
