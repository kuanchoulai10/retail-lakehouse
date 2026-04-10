"""Integration test: full CRUD lifecycle via HTTP with InMemoryJobsRepo."""

from api.jobs import router
from api.jobs._deps import get_repo
from fastapi import FastAPI
from fastapi.testclient import TestClient
from repos import InMemoryJobsRepo


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    repo = InMemoryJobsRepo()
    app.dependency_overrides[get_repo] = lambda: repo
    return app


REWRITE_PAYLOAD = {
    "job_type": "rewrite_data_files",
    "catalog": "retail",
    "spark_conf": {},
    "rewrite_data_files": {"table": "inventory.orders"},
}

EXPIRE_PAYLOAD = {
    "job_type": "expire_snapshots",
    "catalog": "retail",
    "spark_conf": {},
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
    name1 = job1["name"]
    assert name1.startswith("table-maintenance-rewrite-data-files-")
    assert job1["kind"] == "SparkApplication"
    assert job1["status"] == "pending"

    # 3. List shows 1 job
    resp = client.get("/v1/jobs")
    assert resp.status_code == 200
    jobs = resp.json()
    assert len(jobs) == 1
    assert jobs[0]["name"] == name1

    # 4. Get by name returns the job
    resp = client.get(f"/v1/jobs/{name1}")
    assert resp.status_code == 200
    assert resp.json()["name"] == name1

    # 5. Create second job (different type)
    resp = client.post("/v1/jobs", json=EXPIRE_PAYLOAD)
    assert resp.status_code == 201
    job2 = resp.json()
    name2 = job2["name"]
    assert name2.startswith("table-maintenance-expire-snapshots-")

    # 6. List shows 2 jobs
    resp = client.get("/v1/jobs")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    # 7. Delete first job
    resp = client.delete(f"/v1/jobs/{name1}")
    assert resp.status_code == 204

    # 8. List shows 1 job (only second remains)
    resp = client.get("/v1/jobs")
    assert resp.status_code == 200
    jobs = resp.json()
    assert len(jobs) == 1
    assert jobs[0]["name"] == name2

    # 9. Get deleted job returns 404
    resp = client.get(f"/v1/jobs/{name1}")
    assert resp.status_code == 404

    # 10. Delete second job
    resp = client.delete(f"/v1/jobs/{name2}")
    assert resp.status_code == 204

    # 11. List is empty again
    resp = client.get("/v1/jobs")
    assert resp.status_code == 200
    assert resp.json() == []

    # 12. Delete already-deleted job returns 404
    resp = client.delete(f"/v1/jobs/{name2}")
    assert resp.status_code == 404
