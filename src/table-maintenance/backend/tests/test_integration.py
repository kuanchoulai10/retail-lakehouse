"""Integration test: full CRUD lifecycle via HTTP with InMemoryJobsRepo."""

from dependencies.use_cases import (
    get_create_job_use_case,
    get_delete_job_use_case,
    get_get_job_use_case,
    get_list_jobs_use_case,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jobs.adapter.inbound.web import router
from jobs.adapter.outbound.in_memory_jobs_repo import InMemoryJobsRepo
from jobs.application.domain.service.create_job import CreateJobService
from jobs.application.domain.service.delete_job import DeleteJobService
from jobs.application.domain.service.get_job import GetJobService
from jobs.application.domain.service.list_jobs import ListJobsService


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    repo = InMemoryJobsRepo()
    app.dependency_overrides[get_create_job_use_case] = lambda: CreateJobService(repo)
    app.dependency_overrides[get_delete_job_use_case] = lambda: DeleteJobService(repo)
    app.dependency_overrides[get_get_job_use_case] = lambda: GetJobService(repo)
    app.dependency_overrides[get_list_jobs_use_case] = lambda: ListJobsService(repo)
    return app


REWRITE_PAYLOAD = {
    "job_type": "rewrite_data_files",
    "catalog": "retail",
    "rewrite_data_files": {"table": "inventory.orders"},
}

EXPIRE_PAYLOAD = {
    "job_type": "expire_snapshots",
    "catalog": "retail",
    "expire_snapshots": {"table": "inventory.orders"},
}


def test_full_crud_lifecycle():
    client = TestClient(_make_app())

    # 1. Empty list at start
    resp = client.get("/v1/jobs")
    assert resp.status_code == 200
    assert resp.json() == []

    # 2. Create first job
    resp = client.post("/v1/jobs", json=REWRITE_PAYLOAD)
    assert resp.status_code == 201
    job1 = resp.json()
    id1 = job1["id"]
    assert len(id1) == 10  # secrets.token_hex(5) produces 10 hex chars
    assert job1["status"] == "pending"

    # 3. List shows 1 job
    resp = client.get("/v1/jobs")
    assert resp.status_code == 200
    jobs = resp.json()
    assert len(jobs) == 1
    assert jobs[0]["id"] == id1

    # 4. Get by id returns the job
    resp = client.get(f"/v1/jobs/{id1}")
    assert resp.status_code == 200
    assert resp.json()["id"] == id1

    # 5. Create second job (different type)
    resp = client.post("/v1/jobs", json=EXPIRE_PAYLOAD)
    assert resp.status_code == 201
    job2 = resp.json()
    id2 = job2["id"]
    assert len(id2) == 10

    # 6. List shows 2 jobs
    resp = client.get("/v1/jobs")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    # 7. Delete first job
    resp = client.delete(f"/v1/jobs/{id1}")
    assert resp.status_code == 204

    # 8. List shows 1 job (only second remains)
    resp = client.get("/v1/jobs")
    assert resp.status_code == 200
    jobs = resp.json()
    assert len(jobs) == 1
    assert jobs[0]["id"] == id2

    # 9. Get deleted job returns 404
    resp = client.get(f"/v1/jobs/{id1}")
    assert resp.status_code == 404

    # 10. Delete second job
    resp = client.delete(f"/v1/jobs/{id2}")
    assert resp.status_code == 204

    # 11. List is empty again
    resp = client.get("/v1/jobs")
    assert resp.status_code == 200
    assert resp.json() == []

    # 12. Delete already-deleted job returns 404
    resp = client.delete(f"/v1/jobs/{id2}")
    assert resp.status_code == 404
