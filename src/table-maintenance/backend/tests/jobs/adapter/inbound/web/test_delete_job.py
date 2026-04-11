from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from jobs.adapter.inbound.web import router
from jobs.adapter.inbound.web.delete_job import _get_use_case
from jobs.application.exceptions import JobNotFoundError
from jobs.application.port.inbound import DeleteJobOutput


def _make_client(use_case: MagicMock) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[_get_use_case] = lambda: use_case
    return TestClient(app)


def test_delete_job_returns_204():
    use_case = MagicMock()
    use_case.execute.return_value = DeleteJobOutput()
    client = _make_client(use_case)

    response = client.delete("/v1/jobs/table-maintenance-rewrite-data-files-abc123")
    assert response.status_code == 204


def test_delete_job_not_found_returns_404():
    use_case = MagicMock()
    use_case.execute.side_effect = JobNotFoundError("nonexistent")
    client = _make_client(use_case)

    response = client.delete("/v1/jobs/nonexistent")
    assert response.status_code == 404
