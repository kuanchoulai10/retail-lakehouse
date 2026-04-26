"""Integration test: full Job + JobRun lifecycle via HTTP."""

from unittest.mock import MagicMock

from bootstrap.dependencies.use_cases import (
    get_create_job_run_use_case,
    get_create_job_use_case,
    get_get_job_run_use_case,
    get_get_job_use_case,
    get_list_job_runs_use_case,
    get_list_jobs_use_case,
    get_update_job_use_case,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient
from adapter.inbound.web import router
from adapter.outbound.job.jobs_in_memory_repo import JobsInMemoryRepo
from adapter.outbound.job_run.job_runs_in_memory_repo import JobRunsInMemoryRepo
from application.service.outbox.event_serializer import EventSerializer
from application.service.job.create_job import CreateJobService
from application.service.job.get_job import GetJobService
from application.service.job.list_jobs import ListJobsService
from application.service.job.update_job import UpdateJobService
from application.service.job_run.create_job_run import CreateJobRunService
from application.service.job_run.get_job_run import GetJobRunService
from application.service.job_run.list_job_runs import ListJobRunsService


def _make_app() -> tuple[FastAPI, JobRunsInMemoryRepo]:
    """Build a FastAPI app wired with in-memory adapters for testing."""
    app = FastAPI()
    app.include_router(router)
    repo = JobsInMemoryRepo()
    runs_repo = JobRunsInMemoryRepo()
    outbox_repo = MagicMock()
    serializer = EventSerializer()

    app.dependency_overrides[get_create_job_use_case] = lambda: CreateJobService(
        repo, outbox_repo, serializer
    )
    app.dependency_overrides[get_get_job_use_case] = lambda: GetJobService(repo)
    app.dependency_overrides[get_list_jobs_use_case] = lambda: ListJobsService(repo)
    app.dependency_overrides[get_update_job_use_case] = lambda: UpdateJobService(
        repo, outbox_repo, serializer
    )
    app.dependency_overrides[get_create_job_run_use_case] = lambda: CreateJobRunService(
        repo,
        runs_repo,
        outbox_repo,
        serializer,
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

    # 5. Now we can trigger a run (async — returns 202 accepted)
    resp = client.post(f"/v1/jobs/{job_id}/runs")
    assert resp.status_code == 202
    assert resp.json() == {"job_id": job_id, "accepted": True}

    # 6. Unknown run returns 404
    resp = client.get("/v1/runs/ghost")
    assert resp.status_code == 404

    # 9. Archive the job (soft delete)
    resp = client.delete(f"/v1/jobs/{job_id}")
    assert resp.status_code == 204

    # 10. Archived job is still retrievable but has status 'archived'
    resp = client.get(f"/v1/jobs/{job_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"


def test_create_with_status_active_allows_immediate_run():
    """Verify that a job created with status=active allows immediate run triggering."""
    app, _ = _make_app()
    client = TestClient(app)

    resp = client.post("/v1/jobs", json={**REWRITE_PAYLOAD, "status": "active"})
    job_id = resp.json()["id"]
    assert resp.json()["status"] == "active"

    resp = client.post(f"/v1/jobs/{job_id}/runs")
    assert resp.status_code == 202


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
