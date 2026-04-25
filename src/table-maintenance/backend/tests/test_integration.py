"""Integration test: full Job + JobRun lifecycle via HTTP."""

from api.dependencies.use_cases import (
    get_create_job_run_use_case,
    get_create_job_use_case,
    get_delete_job_use_case,
    get_get_job_run_use_case,
    get_get_job_use_case,
    get_list_job_runs_use_case,
    get_list_jobs_use_case,
    get_update_job_use_case,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.adapter.inbound.web import router
from core.adapter.outbound.job.jobs_in_memory_repo import JobsInMemoryRepo
from core.adapter.outbound.job_run.job_runs_in_memory_repo import JobRunsInMemoryRepo
from core.application.service.job.create_job import CreateJobService
from core.application.service.job.delete_job import DeleteJobService
from core.application.service.job.get_job import GetJobService
from core.application.service.job.list_jobs import ListJobsService
from core.application.service.job.update_job import UpdateJobService
from core.application.service.job_run.create_job_run import CreateJobRunService
from core.application.service.job_run.get_job_run import GetJobRunService
from core.application.service.job_run.list_job_runs import ListJobRunsService


def _make_app() -> tuple[FastAPI, JobRunsInMemoryRepo]:
    """Build a FastAPI app wired with in-memory adapters for testing."""
    app = FastAPI()
    app.include_router(router)
    repo = JobsInMemoryRepo()
    runs_repo = JobRunsInMemoryRepo()

    app.dependency_overrides[get_create_job_use_case] = lambda: CreateJobService(repo)
    app.dependency_overrides[get_delete_job_use_case] = lambda: DeleteJobService(repo)
    app.dependency_overrides[get_get_job_use_case] = lambda: GetJobService(repo)
    app.dependency_overrides[get_list_jobs_use_case] = lambda: ListJobsService(repo)
    app.dependency_overrides[get_update_job_use_case] = lambda: UpdateJobService(repo)
    app.dependency_overrides[get_create_job_run_use_case] = lambda: CreateJobRunService(
        repo, runs_repo
    )
    app.dependency_overrides[get_list_job_runs_use_case] = lambda: ListJobRunsService(
        runs_repo
    )
    app.dependency_overrides[get_get_job_run_use_case] = lambda: GetJobRunService(
        runs_repo
    )
    return app, runs_repo


REWRITE_PAYLOAD = {
    "job_type": "rewrite_data_files",
    "catalog": "retail",
    "rewrite_data_files": {"table": "inventory.orders"},
}


def test_full_job_and_run_lifecycle():
    """Verify that a job can be created, enabled, triggered, listed, and deleted."""
    app, _ = _make_app()
    client = TestClient(app)

    # 1. Empty list
    assert client.get("/v1/jobs").json() == []

    # 2. Create job as paused
    resp = client.post("/v1/jobs", json={**REWRITE_PAYLOAD, "status": "paused"})
    assert resp.status_code == 201
    job = resp.json()
    job_id = job["id"]
    assert job["status"] == "paused"

    # 3. Triggering a run while disabled is rejected with 409
    resp = client.post(f"/v1/jobs/{job_id}/runs")
    assert resp.status_code == 409
    assert job_id in resp.json()["detail"]

    # 4. Enable via PATCH
    resp = client.patch(f"/v1/jobs/{job_id}", json={"status": "active"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"

    # 5. Now we can trigger a run
    resp = client.post(f"/v1/jobs/{job_id}/runs")
    assert resp.status_code == 201
    run = resp.json()
    assert run["job_id"] == job_id
    assert run["status"] == "pending"
    run_id = run["run_id"]

    # 6. List runs for the job
    resp = client.get(f"/v1/jobs/{job_id}/runs")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["run_id"] == run_id

    # 7. Get the specific run
    resp = client.get(f"/v1/runs/{run_id}")
    assert resp.status_code == 200
    assert resp.json()["run_id"] == run_id

    # 8. Unknown run returns 404
    resp = client.get("/v1/runs/ghost")
    assert resp.status_code == 404

    # 9. Delete the job
    resp = client.delete(f"/v1/jobs/{job_id}")
    assert resp.status_code == 204

    # 10. Get deleted returns 404
    resp = client.get(f"/v1/jobs/{job_id}")
    assert resp.status_code == 404


def test_create_with_status_active_allows_immediate_run():
    """Verify that a job created with status=active allows immediate run triggering."""
    app, _ = _make_app()
    client = TestClient(app)

    resp = client.post("/v1/jobs", json={**REWRITE_PAYLOAD, "status": "active"})
    job_id = resp.json()["id"]
    assert resp.json()["status"] == "active"

    resp = client.post(f"/v1/jobs/{job_id}/runs")
    assert resp.status_code == 201


def test_patch_unknown_job_returns_404():
    """Verify that patching a nonexistent job returns 404."""
    app, _ = _make_app()
    client = TestClient(app)

    resp = client.patch("/v1/jobs/ghost", json={"status": "active"})
    assert resp.status_code == 404


def test_trigger_run_for_unknown_job_returns_404():
    """Verify that triggering a run for a nonexistent job returns 404."""
    app, _ = _make_app()
    client = TestClient(app)

    resp = client.post("/v1/jobs/ghost/runs")
    assert resp.status_code == 404
