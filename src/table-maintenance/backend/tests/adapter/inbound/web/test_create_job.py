from datetime import UTC, datetime
from unittest.mock import MagicMock

from dependencies.use_cases import get_create_job_use_case
from fastapi import FastAPI
from fastapi.testclient import TestClient
from adapter.inbound.web import router
from application.port.inbound import CreateJobOutput


def _make_client(use_case: MagicMock) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_create_job_use_case] = lambda: use_case
    return TestClient(app)


SAMPLE_OUTPUT = CreateJobOutput(
    id="abc1234567",
    job_type="rewrite_data_files",
    status="pending",
    created_at=datetime(2026, 4, 11, tzinfo=UTC),
)


def test_post_job_returns_201():
    use_case = MagicMock()
    use_case.execute.return_value = SAMPLE_OUTPUT
    client = _make_client(use_case)

    payload = {
        "job_type": "rewrite_data_files",
        "catalog": "retail",
        "spark_conf": {},
        "rewrite_data_files": {"table": "inventory.orders"},
    }
    response = client.post("/v1/jobs", json=payload)
    assert response.status_code == 201
    assert response.json()["id"] == "abc1234567"
    assert response.json()["status"] == "pending"


def test_post_job_missing_catalog_returns_422():
    use_case = MagicMock()
    client = _make_client(use_case)

    payload = {"job_type": "rewrite_data_files", "spark_conf": {}}
    response = client.post("/v1/jobs", json=payload)
    assert response.status_code == 422
