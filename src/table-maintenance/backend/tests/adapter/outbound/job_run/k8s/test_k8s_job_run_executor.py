"""Tests for JobRunK8sExecutor."""

from unittest.mock import MagicMock

from adapter.outbound.job_run.k8s.job_run_k8s_executor import JobRunK8sExecutor
from adapter.outbound.job_run.k8s.k8s_executor_config import K8sExecutorConfig
from application.port.outbound.job_run.job_run_executor import JobRunExecutor
from application.port.outbound.job_run.job_submission import JobSubmission


def _config() -> K8sExecutorConfig:
    return K8sExecutorConfig(
        namespace="spark-jobs",
        image="localhost:5000/table-maintenance-jobs:latest",
        image_pull_policy="Never",
        spark_version="4.0.0",
        service_account="spark-operator-spark",
        iceberg_jar="https://repo1.maven.org/iceberg-spark.jar",
        iceberg_aws_jar="https://repo1.maven.org/iceberg-aws.jar",
    )


def _submission(**overrides) -> JobSubmission:
    defaults = {
        "run_id": "j1-abc123",
        "job_id": "j1",
        "job_type": "expire_snapshots",
        "catalog": "retail",
        "table": "inventory.orders",
        "job_config": {"retain_last": 5},
        "driver_memory": "2g",
        "executor_memory": "4g",
        "executor_instances": 2,
        "cron_expression": None,
    }
    defaults.update(overrides)
    return JobSubmission(**defaults)  # type: ignore[arg-type]


def test_is_subclass_of_job_run_executor():
    """Verify JobRunK8sExecutor implements the JobRunExecutor interface."""
    api = MagicMock()
    executor = JobRunK8sExecutor(api, _config())
    assert isinstance(executor, JobRunExecutor)


def test_submit_calls_create_namespaced_custom_object():
    """Verify submit calls the K8s API."""
    api = MagicMock()
    executor = JobRunK8sExecutor(api, _config())
    executor.submit(_submission())
    api.create_namespaced_custom_object.assert_called_once()


def test_submit_uses_spark_plural_for_non_cron():
    """Verify submit uses sparkapplications plural when no cron."""
    api = MagicMock()
    executor = JobRunK8sExecutor(api, _config())
    executor.submit(_submission(cron_expression=None))
    call_kwargs = api.create_namespaced_custom_object.call_args.kwargs
    assert call_kwargs["plural"] == "sparkapplications"


def test_submit_uses_scheduled_plural_for_cron():
    """Verify submit uses scheduledsparkapplications plural when cron set."""
    api = MagicMock()
    executor = JobRunK8sExecutor(api, _config())
    executor.submit(_submission(cron_expression="0 2 * * *"))
    call_kwargs = api.create_namespaced_custom_object.call_args.kwargs
    assert call_kwargs["plural"] == "scheduledsparkapplications"


def test_submit_uses_config_namespace():
    """Verify submit passes the config namespace to K8s API."""
    api = MagicMock()
    executor = JobRunK8sExecutor(api, _config())
    executor.submit(_submission())
    call_kwargs = api.create_namespaced_custom_object.call_args.kwargs
    assert call_kwargs["namespace"] == "spark-jobs"


def test_submit_returns_none():
    """Verify submit returns None — no entity creation."""
    api = MagicMock()
    executor = JobRunK8sExecutor(api, _config())
    result = executor.submit(_submission())
    assert result is None
