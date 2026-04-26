"""Tests for JobRunK8sExecutor."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from core.adapter.outbound.job_run.k8s.job_run_k8s_executor import JobRunK8sExecutor
from application.domain.model.job import (
    CronExpression,
    Job,
    JobId,
    JobType,
    TableReference,
)
from application.domain.model.job_run import JobRunStatus
from application.port.outbound.job_run.job_run_executor import JobRunExecutor
from core.configs import AppSettings


SETTINGS = AppSettings()


def _make_job(job_id: str = "abc1234567", cron: str | None = None) -> Job:
    """Provide a sample Job entity with optional overrides."""
    now = datetime.now(UTC)
    return Job(
        id=JobId(value=job_id),
        job_type=JobType.REWRITE_DATA_FILES,
        created_at=now,
        updated_at=now,
        table_ref=TableReference(catalog="retail", table="inventory.orders"),
        cron=CronExpression(expression=cron) if cron else None,
    )


def test_is_subclass_of_job_run_executor():
    """Verify that JobRunK8sExecutor implements the JobRunExecutor interface."""
    api = MagicMock()
    executor = JobRunK8sExecutor(api, SETTINGS)
    assert isinstance(executor, JobRunExecutor)


def test_trigger_calls_create_namespaced_custom_object():
    """Verify that trigger calls the K8s API to create a custom object."""
    api = MagicMock()
    api.create_namespaced_custom_object.return_value = {
        "metadata": {"name": "abc1234567-d3adbe"},
        "kind": "SparkApplication",
    }
    executor = JobRunK8sExecutor(api, SETTINGS)
    executor.trigger(_make_job())
    api.create_namespaced_custom_object.assert_called_once()


def test_trigger_uses_scheduled_plural_when_cron_set():
    """Verify that trigger uses the scheduled plural when a cron is set."""
    api = MagicMock()
    api.create_namespaced_custom_object.return_value = {
        "metadata": {"name": "abc1234567"},
        "kind": "ScheduledSparkApplication",
    }
    executor = JobRunK8sExecutor(api, SETTINGS)
    executor.trigger(_make_job(cron="0 2 * * *"))
    call_kwargs = api.create_namespaced_custom_object.call_args.kwargs
    assert call_kwargs["plural"] == "scheduledsparkapplications"


def test_trigger_uses_spark_plural_for_non_cron_job():
    """Verify that trigger uses the spark plural for a non-cron job."""
    api = MagicMock()
    api.create_namespaced_custom_object.return_value = {
        "metadata": {"name": "abc1234567-d3adbe"},
        "kind": "SparkApplication",
    }
    executor = JobRunK8sExecutor(api, SETTINGS)
    executor.trigger(_make_job())
    call_kwargs = api.create_namespaced_custom_object.call_args.kwargs
    assert call_kwargs["plural"] == "sparkapplications"


def test_trigger_returns_job_run_linked_to_job_id():
    """Verify that the returned run is linked to the correct job id."""
    api = MagicMock()
    api.create_namespaced_custom_object.return_value = {
        "metadata": {"name": "abc1234567-d3adbe"},
        "kind": "SparkApplication",
    }
    executor = JobRunK8sExecutor(api, SETTINGS)
    run = executor.trigger(_make_job("abc1234567"))
    assert run.job_id == JobId(value="abc1234567")


def test_trigger_returns_pending_status():
    """Verify that the returned run has pending status."""
    api = MagicMock()
    api.create_namespaced_custom_object.return_value = {
        "metadata": {"name": "abc1234567-d3adbe"},
        "kind": "SparkApplication",
    }
    executor = JobRunK8sExecutor(api, SETTINGS)
    run = executor.trigger(_make_job())
    assert run.status == JobRunStatus.PENDING


def test_trigger_uses_scheduled_metadata_name_equal_to_job_id():
    """Verify that ScheduledSparkApplication uses the job id as its name."""
    api = MagicMock()
    api.create_namespaced_custom_object.return_value = {
        "metadata": {"name": "abc1234567"},
        "kind": "ScheduledSparkApplication",
    }
    executor = JobRunK8sExecutor(api, SETTINGS)
    executor.trigger(_make_job("abc1234567", cron="0 2 * * *"))
    manifest = api.create_namespaced_custom_object.call_args.kwargs["body"]
    assert manifest["metadata"]["name"] == "abc1234567"


def test_trigger_uses_spark_metadata_name_unique_per_run():
    """Verify that SparkApplication uses a unique name per run."""
    api = MagicMock()
    api.create_namespaced_custom_object.return_value = {
        "metadata": {"name": "unused"},
        "kind": "SparkApplication",
    }
    executor = JobRunK8sExecutor(api, SETTINGS)
    executor.trigger(_make_job("abc1234567"))
    manifest = api.create_namespaced_custom_object.call_args.kwargs["body"]
    name = manifest["metadata"]["name"]
    assert name.startswith("abc1234567-")
    assert name != "abc1234567"
