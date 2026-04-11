from unittest.mock import MagicMock, patch

import pytest
from jobs.adapter.inbound.web.dto import JobApiRequest
from jobs.adapter.outbound.k8s.k8s_jobs_repo import K8sJobsRepo
from jobs.application.domain import JobNotFoundError, JobStatus, JobType
from jobs.application.port.outbound.jobs_repo import BaseJobsRepo
from kubernetes.client.exceptions import ApiException
from shared.configs import AppSettings

SETTINGS = AppSettings()

MOCK_SPARK_APP = {
    "kind": "SparkApplication",
    "metadata": {
        "name": "table-maintenance-rewrite-data-files-abc123",
        "namespace": "default",
        "creationTimestamp": "2026-04-04T10:00:00Z",
    },
    "spec": {
        "driver": {
            "env": [
                {"name": "GLAC_JOB_TYPE", "value": "rewrite_data_files"},
            ]
        }
    },
    "status": {"applicationState": {"state": "COMPLETED"}},
}


def _make_request() -> JobApiRequest:
    return JobApiRequest(
        job_type="rewrite_data_files",
        catalog="retail",
        spark_conf={},
        rewrite_data_files={"table": "inventory.orders"},
    )


def test_is_subclass_of_jobs_repo():
    api = MagicMock()
    repo = K8sJobsRepo(api, SETTINGS)
    assert isinstance(repo, BaseJobsRepo)


def test_create_returns_job():
    api = MagicMock()
    api.create_namespaced_custom_object.return_value = MOCK_SPARK_APP
    repo = K8sJobsRepo(api, SETTINGS)

    patch_target = "jobs.adapter.outbound.k8s.k8s_jobs_repo._generate_name"
    with patch(patch_target, return_value="table-maintenance-rewrite-data-files-abc123"):
        job = repo.create(_make_request())

    assert job.id.value == "table-maintenance-rewrite-data-files-abc123"
    assert job.status == JobStatus.COMPLETED
    assert job.job_type == JobType.REWRITE_DATA_FILES
    api.create_namespaced_custom_object.assert_called_once()
    call_kwargs = api.create_namespaced_custom_object.call_args.kwargs
    assert call_kwargs["plural"] == "sparkapplications"


def test_create_scheduled_uses_correct_plural():
    api = MagicMock()
    scheduled_app = {**MOCK_SPARK_APP, "kind": "ScheduledSparkApplication"}
    api.create_namespaced_custom_object.return_value = scheduled_app
    repo = K8sJobsRepo(api, SETTINGS)

    req = _make_request()
    req.cron = "0 2 * * *"

    with patch("jobs.adapter.outbound.k8s.k8s_jobs_repo._generate_name", return_value="my-job"):
        repo.create(req)

    call_kwargs = api.create_namespaced_custom_object.call_args.kwargs
    assert call_kwargs["plural"] == "scheduledsparkapplications"


def test_list_merges_both_kinds():
    api = MagicMock()
    api.list_namespaced_custom_object.side_effect = [
        {"items": [MOCK_SPARK_APP]},
        {"items": []},
    ]
    repo = K8sJobsRepo(api, SETTINGS)
    results = repo.list_all()
    assert len(results) == 1
    assert api.list_namespaced_custom_object.call_count == 2


def test_get_tries_spark_application_first():
    api = MagicMock()
    api.get_namespaced_custom_object.return_value = MOCK_SPARK_APP
    repo = K8sJobsRepo(api, SETTINGS)

    job = repo.get("table-maintenance-rewrite-data-files-abc123")

    assert job.id.value == "table-maintenance-rewrite-data-files-abc123"
    first_call = api.get_namespaced_custom_object.call_args_list[0].kwargs
    assert first_call["plural"] == "sparkapplications"


def test_get_falls_back_to_scheduled():
    api = MagicMock()
    scheduled_app = {
        **MOCK_SPARK_APP,
        "kind": "ScheduledSparkApplication",
        "spec": {"template": {"driver": {"env": [{"name": "GLAC_JOB_TYPE", "value": "rewrite_data_files"}]}}},
    }
    not_found = ApiException(status=404)
    api.get_namespaced_custom_object.side_effect = [not_found, scheduled_app]
    repo = K8sJobsRepo(api, SETTINGS)

    job = repo.get("my-job")
    assert job.status == JobStatus.RUNNING


def test_get_raises_not_found():
    api = MagicMock()
    api.get_namespaced_custom_object.side_effect = ApiException(status=404)
    repo = K8sJobsRepo(api, SETTINGS)

    with pytest.raises(JobNotFoundError) as exc_info:
        repo.get("nonexistent")
    assert exc_info.value.name == "nonexistent"


def test_delete_calls_correct_plural():
    api = MagicMock()
    api.delete_namespaced_custom_object.return_value = {}
    repo = K8sJobsRepo(api, SETTINGS)

    repo.delete("table-maintenance-rewrite-data-files-abc123")
    call_kwargs = api.delete_namespaced_custom_object.call_args.kwargs
    assert call_kwargs["plural"] == "sparkapplications"


def test_delete_raises_not_found():
    api = MagicMock()
    api.delete_namespaced_custom_object.side_effect = ApiException(status=404)
    repo = K8sJobsRepo(api, SETTINGS)

    with pytest.raises(JobNotFoundError):
        repo.delete("nonexistent")
