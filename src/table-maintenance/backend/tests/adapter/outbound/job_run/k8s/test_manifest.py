"""Tests for build_manifest."""

from adapter.outbound.job_run.k8s.k8s_executor_config import K8sExecutorConfig
from adapter.outbound.job_run.k8s.manifest import build_manifest
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


def _sub(**overrides) -> JobSubmission:
    defaults = {
        "run_id": "my-job-abc123",
        "job_id": "my-job",
        "job_type": "rewrite_data_files",
        "catalog": "retail",
        "table": "inventory.orders",
        "job_config": {},
        "driver_memory": "512m",
        "executor_memory": "1g",
        "executor_instances": 1,
        "cron_expression": None,
    }
    defaults.update(overrides)
    return JobSubmission(**defaults)  # type: ignore[arg-type]


def test_kind_is_spark_application_without_cron():
    """Verify that the kind is SparkApplication when no cron is set."""
    manifest = build_manifest(_sub(), _config())
    assert manifest["kind"] == "SparkApplication"
    assert manifest["apiVersion"] == "sparkoperator.k8s.io/v1beta2"


def test_name_and_namespace():
    """Verify that the manifest sets name and namespace correctly."""
    manifest = build_manifest(_sub(), _config())
    assert manifest["metadata"]["name"] == "my-job-abc123"
    assert manifest["metadata"]["namespace"] == "spark-jobs"


def test_manifest_includes_job_id_label():
    """Verify that the manifest includes the job-id label."""
    manifest = build_manifest(_sub(job_id="job-xyz"), _config())
    assert manifest["metadata"]["labels"]["table-maintenance/job-id"] == "job-xyz"


def test_driver_env_glac_vars():
    """Verify that driver env contains GLAC configuration variables."""
    manifest = build_manifest(_sub(job_config={"rewrite_all": True}), _config())
    env = {e["name"]: e["value"] for e in manifest["spec"]["driver"]["env"]}
    assert env["GLAC_JOB_TYPE"] == "rewrite_data_files"
    assert env["GLAC_CATALOG"] == "retail"
    assert env["GLAC_REWRITE_DATA_FILES__REWRITE_ALL"] == "true"


def test_strategy_enum_serialized_as_value():
    """Verify that strategy enum is serialized as its string value."""
    manifest = build_manifest(
        _sub(job_config={"table": "inventory.orders", "strategy": "sort"}), _config()
    )
    env = {e["name"]: e["value"] for e in manifest["spec"]["driver"]["env"]}
    assert env["GLAC_REWRITE_DATA_FILES__STRATEGY"] == "sort"


def test_expire_snapshots_datetime_env():
    """Verify that expire_snapshots env vars include the datetime value."""
    manifest = build_manifest(
        _sub(
            job_type="expire_snapshots",
            job_config={
                "table": "inventory.orders",
                "older_than": "2026-01-01T12:00:00+00:00",
            },
        ),
        _config(),
    )
    env = {e["name"]: e["value"] for e in manifest["spec"]["driver"]["env"]}
    assert env["GLAC_EXPIRE_SNAPSHOTS__TABLE"] == "inventory.orders"
    assert "2026-01-01" in env["GLAC_EXPIRE_SNAPSHOTS__OLDER_THAN"]


def test_executor_env_has_aws_vars():
    """Verify that executor env includes AWS credential variables."""
    manifest = build_manifest(_sub(), _config())
    exec_env_keys = {e["name"] for e in manifest["spec"]["executor"]["env"]}
    assert "AWS_ACCESS_KEY_ID" in exec_env_keys
    assert "AWS_SECRET_ACCESS_KEY" in exec_env_keys


def test_resource_values_from_submission():
    """Verify that resource values come from the submission, not system config."""
    manifest = build_manifest(
        _sub(driver_memory="2g", executor_memory="4g", executor_instances=3), _config()
    )
    assert manifest["spec"]["driver"]["memory"] == "2g"
    assert manifest["spec"]["executor"]["memory"] == "4g"
    assert manifest["spec"]["executor"]["instances"] == 3


def test_cron_creates_scheduled_spark_application():
    """Verify that a cron job produces a ScheduledSparkApplication manifest."""
    manifest = build_manifest(_sub(cron_expression="0 2 * * *"), _config())
    assert manifest["kind"] == "ScheduledSparkApplication"
    assert manifest["spec"]["schedule"] == "0 2 * * *"
    assert "type" in manifest["spec"]["template"]


def test_none_fields_not_in_env():
    """Verify that None-valued fields are omitted from the env vars."""
    manifest = build_manifest(_sub(), _config())
    env_names = {e["name"] for e in manifest["spec"]["driver"]["env"]}
    assert "GLAC_REWRITE_DATA_FILES__SORT_ORDER" not in env_names
    assert "GLAC_REWRITE_DATA_FILES__WHERE" not in env_names
