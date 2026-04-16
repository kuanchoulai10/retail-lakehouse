from unittest.mock import MagicMock

import pytest
from kubernetes.client.exceptions import ApiException

from adapter.outbound.k8s.k8s_job_runs_repo import K8sJobRunsRepo
from application.domain.model.exceptions import JobRunNotFoundError
from application.domain.model.job_id import JobId
from application.domain.model.job_run_id import JobRunId
from application.domain.model.job_run_status import JobRunStatus
from application.port.outbound.job_runs_repo import BaseJobRunsRepo
from configs import AppSettings

SETTINGS = AppSettings()

MOCK_SPARK_APP = {
    "kind": "SparkApplication",
    "metadata": {
        "name": "job-1-abc",
        "namespace": "default",
        "creationTimestamp": "2026-04-04T10:00:00Z",
        "labels": {"table-maintenance/job-id": "job-1"},
    },
    "status": {"applicationState": {"state": "RUNNING"}},
}

MOCK_SCHEDULED = {
    "kind": "ScheduledSparkApplication",
    "metadata": {
        "name": "job-2",
        "namespace": "default",
        "creationTimestamp": "2026-04-04T10:00:00Z",
        "labels": {"table-maintenance/job-id": "job-2"},
    },
    "status": {},
}


def test_is_subclass_of_base_job_runs_repo():
    api = MagicMock()
    repo = K8sJobRunsRepo(api, SETTINGS)
    assert isinstance(repo, BaseJobRunsRepo)


def test_get_returns_job_run_from_spark_app():
    api = MagicMock()
    api.get_namespaced_custom_object.return_value = MOCK_SPARK_APP
    repo = K8sJobRunsRepo(api, SETTINGS)

    run = repo.get(JobRunId(value="job-1-abc"))

    assert run.id.value == "job-1-abc"
    assert run.job_id == JobId(value="job-1")
    assert run.status == JobRunStatus.RUNNING


def test_get_falls_back_to_scheduled():
    api = MagicMock()
    api.get_namespaced_custom_object.side_effect = [
        ApiException(status=404),
        MOCK_SCHEDULED,
    ]
    repo = K8sJobRunsRepo(api, SETTINGS)

    run = repo.get(JobRunId(value="job-2"))

    assert run.id.value == "job-2"
    assert run.job_id == JobId(value="job-2")
    assert run.status == JobRunStatus.RUNNING


def test_get_raises_job_run_not_found():
    api = MagicMock()
    api.get_namespaced_custom_object.side_effect = ApiException(status=404)
    repo = K8sJobRunsRepo(api, SETTINGS)

    with pytest.raises(JobRunNotFoundError) as exc_info:
        repo.get(JobRunId(value="missing"))
    assert exc_info.value.run_id == "missing"


def test_list_for_job_filters_by_label_selector():
    api = MagicMock()
    api.list_namespaced_custom_object.side_effect = [
        {"items": [MOCK_SPARK_APP]},
        {"items": []},
    ]
    repo = K8sJobRunsRepo(api, SETTINGS)

    runs = repo.list_for_job(JobId(value="job-1"))

    assert len(runs) == 1
    call_kwargs = api.list_namespaced_custom_object.call_args_list[0].kwargs
    assert call_kwargs["label_selector"] == "table-maintenance/job-id=job-1"


def test_list_all_merges_both_kinds():
    api = MagicMock()
    api.list_namespaced_custom_object.side_effect = [
        {"items": [MOCK_SPARK_APP]},
        {"items": [MOCK_SCHEDULED]},
    ]
    repo = K8sJobRunsRepo(api, SETTINGS)

    runs = repo.list_all()

    assert len(runs) == 2
    assert api.list_namespaced_custom_object.call_count == 2
