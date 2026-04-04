from unittest.mock import MagicMock, patch

import pytest
from config import AppSettings
from configs.base import JobType
from configs.jobs.rewrite_data_files import RewriteDataFilesConfig
from fastapi import HTTPException
from k8s.jobs_repo import JobsRepository
from kubernetes.client.exceptions import ApiException
from models.requests import JobRequest
from models.responses import JobStatus

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


def _make_request() -> JobRequest:
    return JobRequest(
        job_type=JobType.REWRITE_DATA_FILES,
        catalog="retail",
        spark_conf={},
        rewrite_data_files=RewriteDataFilesConfig(table="inventory.orders"),
    )


def test_create_returns_job_response():
    api = MagicMock()
    api.create_namespaced_custom_object.return_value = MOCK_SPARK_APP
    repo = JobsRepository(api, SETTINGS)

    with patch("k8s.jobs_repo._generate_name", return_value="table-maintenance-rewrite-data-files-abc123"):
        response = repo.create(_make_request())

    assert response.name == "table-maintenance-rewrite-data-files-abc123"
    assert response.kind == "SparkApplication"
    assert response.status == JobStatus.COMPLETED
    assert response.job_type == JobType.REWRITE_DATA_FILES
    api.create_namespaced_custom_object.assert_called_once()
    call_kwargs = api.create_namespaced_custom_object.call_args.kwargs
    assert call_kwargs["plural"] == "sparkapplications"


def test_create_scheduled_uses_correct_plural():
    api = MagicMock()
    scheduled_app = {**MOCK_SPARK_APP, "kind": "ScheduledSparkApplication"}
    api.create_namespaced_custom_object.return_value = scheduled_app
    repo = JobsRepository(api, SETTINGS)

    req = _make_request()
    req.cron = "0 2 * * *"

    with patch("k8s.jobs_repo._generate_name", return_value="my-job"):
        repo.create(req)

    call_kwargs = api.create_namespaced_custom_object.call_args.kwargs
    assert call_kwargs["plural"] == "scheduledsparkapplications"


def test_list_merges_both_kinds():
    api = MagicMock()
    api.list_namespaced_custom_object.side_effect = [
        {"items": [MOCK_SPARK_APP]},
        {"items": []},
    ]
    repo = JobsRepository(api, SETTINGS)
    results = repo.list()
    assert len(results) == 1
    assert api.list_namespaced_custom_object.call_count == 2


def test_get_tries_spark_application_first():
    api = MagicMock()
    api.get_namespaced_custom_object.return_value = MOCK_SPARK_APP
    repo = JobsRepository(api, SETTINGS)

    response = repo.get("table-maintenance-rewrite-data-files-abc123")

    assert response.name == "table-maintenance-rewrite-data-files-abc123"
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
    repo = JobsRepository(api, SETTINGS)

    response = repo.get("my-job")
    assert response.kind == "ScheduledSparkApplication"


def test_get_raises_404_when_not_found():
    api = MagicMock()
    api.get_namespaced_custom_object.side_effect = ApiException(status=404)
    repo = JobsRepository(api, SETTINGS)

    with pytest.raises(HTTPException) as exc_info:
        repo.get("nonexistent")
    assert exc_info.value.status_code == 404


def test_delete_calls_correct_plural():
    api = MagicMock()
    api.delete_namespaced_custom_object.return_value = {}
    repo = JobsRepository(api, SETTINGS)

    repo.delete("table-maintenance-rewrite-data-files-abc123")
    call_kwargs = api.delete_namespaced_custom_object.call_args.kwargs
    assert call_kwargs["plural"] == "sparkapplications"


def test_delete_raises_404_when_not_found():
    api = MagicMock()
    api.delete_namespaced_custom_object.side_effect = ApiException(status=404)
    repo = JobsRepository(api, SETTINGS)

    with pytest.raises(HTTPException) as exc_info:
        repo.delete("nonexistent")
    assert exc_info.value.status_code == 404
