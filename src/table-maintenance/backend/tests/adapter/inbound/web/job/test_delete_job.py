"""Tests for delete job endpoint (archives via UpdateJobUseCase)."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from bootstrap.dependencies.use_cases import get_update_job_use_case
from fastapi import FastAPI
from fastapi.testclient import TestClient
from adapter.inbound.web import router
from application.exceptions import JobNotFoundError
from application.port.inbound import UpdateJobUseCaseOutput


def _make_client(use_case: MagicMock) -> TestClient:
    """Provide a test client with the update-job use case overridden."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_update_job_use_case] = lambda: use_case
    return TestClient(app)


def test_delete_job_returns_204():
    """Return 204 with no content when the job is successfully archived."""
    now = datetime.now(UTC)
    use_case = MagicMock()
    use_case.execute.return_value = UpdateJobUseCaseOutput(
        id="abc123",
        job_type="rewrite_data_files",
        status="archived",
        created_at=now,
        updated_at=now,
    )
    client = _make_client(use_case)

    response = client.delete("/v1/jobs/table-maintenance-rewrite-data-files-abc123")
    assert response.status_code == 204


def test_delete_job_not_found_returns_404():
    """Return 404 when the job to archive does not exist."""
    use_case = MagicMock()
    use_case.execute.side_effect = JobNotFoundError("nonexistent")
    client = _make_client(use_case)

    response = client.delete("/v1/jobs/nonexistent")
    assert response.status_code == 404
