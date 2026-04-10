import pytest
from configs import JobType
from configs.jobs.rewrite_data_files import RewriteDataFilesConfig
from models import JobRequest, JobStatus
from repos import BaseJobsRepo, InMemoryJobsRepo, JobNotFoundError


def _make_request(
    job_type: JobType = JobType.REWRITE_DATA_FILES,
    cron: str | None = None,
) -> JobRequest:
    return JobRequest(
        job_type=job_type,
        catalog="retail",
        spark_conf={},
        rewrite_data_files=RewriteDataFilesConfig(table="inventory.orders"),
        cron=cron,
    )


def test_is_subclass_of_jobs_repo():
    repo = InMemoryJobsRepo()
    assert isinstance(repo, BaseJobsRepo)


def test_create_returns_response_with_name():
    repo = InMemoryJobsRepo()
    resp = repo.create(_make_request())
    assert resp.name.startswith("table-maintenance-rewrite-data-files-")
    assert resp.job_type == JobType.REWRITE_DATA_FILES
    assert resp.kind == "SparkApplication"
    assert resp.status == JobStatus.PENDING


def test_create_scheduled_sets_kind():
    repo = InMemoryJobsRepo()
    resp = repo.create(_make_request(cron="0 2 * * *"))
    assert resp.kind == "ScheduledSparkApplication"
    assert resp.status == JobStatus.RUNNING


def test_list_all_empty():
    repo = InMemoryJobsRepo()
    assert repo.list_all() == []


def test_list_all_returns_created_jobs():
    repo = InMemoryJobsRepo()
    repo.create(_make_request())
    repo.create(_make_request())
    assert len(repo.list_all()) == 2


def test_get_returns_created_job():
    repo = InMemoryJobsRepo()
    created = repo.create(_make_request())
    fetched = repo.get(created.name)
    assert fetched.name == created.name


def test_get_raises_not_found():
    repo = InMemoryJobsRepo()
    with pytest.raises(JobNotFoundError) as exc_info:
        repo.get("nonexistent")
    assert exc_info.value.name == "nonexistent"


def test_delete_removes_job():
    repo = InMemoryJobsRepo()
    created = repo.create(_make_request())
    repo.delete(created.name)
    assert repo.list_all() == []


def test_delete_raises_not_found():
    repo = InMemoryJobsRepo()
    with pytest.raises(JobNotFoundError):
        repo.delete("nonexistent")
