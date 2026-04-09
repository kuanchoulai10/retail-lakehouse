from unittest.mock import MagicMock

from api.routes import router
from api.routes._deps import get_repo
from fastapi import FastAPI
from fastapi.testclient import TestClient
from repos.base import JobNotFoundError


def _make_client(repo: MagicMock) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_repo] = lambda: repo
    return TestClient(app)


def test_delete_job_returns_204():
    repo = MagicMock()
    repo.delete.return_value = None
    client = _make_client(repo)

    response = client.delete("/jobs/table-maintenance-rewrite-data-files-abc123")
    assert response.status_code == 204


def test_delete_job_not_found_returns_404():
    repo = MagicMock()
    repo.delete.side_effect = JobNotFoundError("nonexistent")
    client = _make_client(repo)

    response = client.delete("/jobs/nonexistent")
    assert response.status_code == 404
