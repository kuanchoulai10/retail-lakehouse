"""Integration test: full Job + JobRun lifecycle via HTTP."""

from dependencies.use_cases import (
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
from adapter.inbound.web import router
from adapter.outbound.in_memory_job_run_executor import InMemoryJobRunExecutor
from adapter.outbound.in_memory_job_runs_repo import InMemoryJobRunsRepo
from adapter.outbound.in_memory_jobs_repo import InMemoryJobsRepo
from application.domain.service.create_job import CreateJobService
from application.domain.service.create_job_run import CreateJobRunService
from application.domain.service.delete_job import DeleteJobService
from application.domain.service.get_job import GetJobService
from application.domain.service.get_job_run import GetJobRunService
from application.domain.service.list_job_runs import ListJobRunsService
from application.domain.service.list_jobs import ListJobsService
from application.domain.service.update_job import UpdateJobService


class _RecordingExecutor(InMemoryJobRunExecutor):
    """Executor that also mirrors every triggered run into a runs repo."""

    def __init__(self, runs_repo: InMemoryJobRunsRepo) -> None:
        super().__init__()
        self._runs_repo = runs_repo

    def trigger(self, job):
        run = super().trigger(job)
        self._runs_repo.add(run)
        return run


def _make_app() -> tuple[FastAPI, InMemoryJobRunsRepo, _RecordingExecutor]:
    app = FastAPI()
    app.include_router(router)
    repo = InMemoryJobsRepo()
    runs_repo = InMemoryJobRunsRepo()
    executor = _RecordingExecutor(runs_repo)

    app.dependency_overrides[get_create_job_use_case] = lambda: CreateJobService(repo)
    app.dependency_overrides[get_delete_job_use_case] = lambda: DeleteJobService(repo)
    app.dependency_overrides[get_get_job_use_case] = lambda: GetJobService(repo)
    app.dependency_overrides[get_list_jobs_use_case] = lambda: ListJobsService(repo)
    app.dependency_overrides[get_update_job_use_case] = lambda: UpdateJobService(repo)
    app.dependency_overrides[get_create_job_run_use_case] = lambda: CreateJobRunService(
        repo, executor
    )
    app.dependency_overrides[get_list_job_runs_use_case] = lambda: ListJobRunsService(
        runs_repo
    )
    app.dependency_overrides[get_get_job_run_use_case] = lambda: GetJobRunService(
        runs_repo
    )
    return app, runs_repo, executor


REWRITE_PAYLOAD = {
    "job_type": "rewrite_data_files",
    "catalog": "retail",
    "rewrite_data_files": {"table": "inventory.orders"},
}


def test_full_job_and_run_lifecycle():
    app, _, _ = _make_app()
    client = TestClient(app)

    # 1. Empty list
    assert client.get("/v1/jobs").json() == []

    # 2. Create job (disabled by default)
    resp = client.post("/v1/jobs", json=REWRITE_PAYLOAD)
    assert resp.status_code == 201
    job = resp.json()
    job_id = job["id"]
    assert job["enabled"] is False

    # 3. Triggering a run while disabled is rejected with 409
    resp = client.post(f"/v1/jobs/{job_id}/runs")
    assert resp.status_code == 409
    assert job_id in resp.json()["detail"]

    # 4. Enable via PATCH
    resp = client.patch(f"/v1/jobs/{job_id}", json={"enabled": True})
    assert resp.status_code == 200
    assert resp.json()["enabled"] is True

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


def test_create_with_enabled_true_allows_immediate_run():
    app, _, _ = _make_app()
    client = TestClient(app)

    resp = client.post("/v1/jobs", json={**REWRITE_PAYLOAD, "enabled": True})
    job_id = resp.json()["id"]
    assert resp.json()["enabled"] is True

    resp = client.post(f"/v1/jobs/{job_id}/runs")
    assert resp.status_code == 201


def test_patch_unknown_job_returns_404():
    app, _, _ = _make_app()
    client = TestClient(app)

    resp = client.patch("/v1/jobs/ghost", json={"enabled": True})
    assert resp.status_code == 404


def test_trigger_run_for_unknown_job_returns_404():
    app, _, _ = _make_app()
    client = TestClient(app)

    resp = client.post("/v1/jobs/ghost/runs")
    assert resp.status_code == 404
