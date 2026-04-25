"""Tests for build_manifest."""

from datetime import UTC, datetime

from adapter.outbound.job_run.k8s.manifest import build_manifest
from application.domain.model.job import (
    CronExpression,
    Job,
    JobId,
    JobType,
    TableReference,
)
from core.configs import AppSettings

SETTINGS = AppSettings()


def _make_job(name: str = "my-job", **kwargs) -> Job:  # type: ignore[no-any-explicit]
    """Provide a sample Job entity with optional overrides."""
    now = datetime.now(UTC)
    defaults: dict = {
        "id": JobId(value=name),
        "job_type": JobType.REWRITE_DATA_FILES,
        "created_at": now,
        "updated_at": now,
        "table_ref": TableReference(catalog="retail", table="inventory.orders"),
        "job_config": {},
    }
    defaults.update(kwargs)
    return Job(**defaults)  # type: ignore[arg-type]


def test_kind_is_spark_application_without_cron():
    """Verify that the kind is SparkApplication when no cron is set."""
    manifest = build_manifest(_make_job(), "my-job-run", SETTINGS)
    assert manifest["kind"] == "SparkApplication"
    assert manifest["apiVersion"] == "sparkoperator.k8s.io/v1beta2"


def test_name_and_namespace():
    """Verify that the manifest sets name and namespace correctly."""
    manifest = build_manifest(_make_job("my-job"), "my-job-abc123", SETTINGS)
    assert manifest["metadata"]["name"] == "my-job-abc123"
    assert manifest["metadata"]["namespace"] == SETTINGS.k8s.namespace


def test_manifest_includes_job_id_label():
    """Verify that the manifest includes the job-id label."""
    manifest = build_manifest(_make_job("job-xyz"), "job-xyz-run1", SETTINGS)
    assert manifest["metadata"]["labels"]["table-maintenance/job-id"] == "job-xyz"


def test_driver_env_glac_vars():
    """Verify that driver env contains GLAC configuration variables."""
    job = _make_job(job_config={"rewrite_all": True})
    manifest = build_manifest(job, "my-job-run", SETTINGS)
    env = {e["name"]: e["value"] for e in manifest["spec"]["driver"]["env"]}
    assert env["GLAC_JOB_TYPE"] == "rewrite_data_files"
    assert env["GLAC_CATALOG"] == "retail"
    assert env["GLAC_REWRITE_DATA_FILES__REWRITE_ALL"] == "true"


def test_strategy_enum_serialized_as_value():
    """Verify that strategy enum is serialized as its string value."""
    job = _make_job(job_config={"table": "inventory.orders", "strategy": "sort"})
    manifest = build_manifest(job, "my-job-run", SETTINGS)
    env = {e["name"]: e["value"] for e in manifest["spec"]["driver"]["env"]}
    assert env["GLAC_REWRITE_DATA_FILES__STRATEGY"] == "sort"


def test_expire_snapshots_datetime_env():
    """Verify that expire_snapshots env vars include the datetime value."""
    dt = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    job = _make_job(
        job_type=JobType.EXPIRE_SNAPSHOTS,
        job_config={"table": "inventory.orders", "older_than": dt.isoformat()},
    )
    manifest = build_manifest(job, "my-job-run", SETTINGS)
    env = {e["name"]: e["value"] for e in manifest["spec"]["driver"]["env"]}
    assert env["GLAC_EXPIRE_SNAPSHOTS__TABLE"] == "inventory.orders"
    assert "2026-01-01" in env["GLAC_EXPIRE_SNAPSHOTS__OLDER_THAN"]


def test_executor_env_has_aws_vars():
    """Verify that executor env includes AWS credential variables."""
    manifest = build_manifest(_make_job(), "my-job-run", SETTINGS)
    exec_env_keys = {e["name"] for e in manifest["spec"]["executor"]["env"]}
    assert "AWS_ACCESS_KEY_ID" in exec_env_keys
    assert "AWS_SECRET_ACCESS_KEY" in exec_env_keys


def test_resource_defaults_from_settings():
    """Verify that resource defaults come from settings."""
    manifest = build_manifest(_make_job(), "my-job-run", SETTINGS)
    assert manifest["spec"]["driver"]["memory"] == "512m"
    assert manifest["spec"]["executor"]["memory"] == "1g"
    assert manifest["spec"]["executor"]["instances"] == 1


def test_cron_creates_scheduled_spark_application():
    """Verify that a cron job produces a ScheduledSparkApplication manifest."""
    job = _make_job(cron=CronExpression(expression="0 2 * * *"))
    manifest = build_manifest(job, "my-job", SETTINGS)
    assert manifest["kind"] == "ScheduledSparkApplication"
    assert manifest["spec"]["schedule"] == "0 2 * * *"
    assert "type" in manifest["spec"]["template"]


def test_none_fields_not_in_env():
    """Verify that None-valued fields are omitted from the env vars."""
    manifest = build_manifest(_make_job(), "my-job-run", SETTINGS)
    env_names = {e["name"] for e in manifest["spec"]["driver"]["env"]}
    assert "GLAC_REWRITE_DATA_FILES__SORT_ORDER" not in env_names
    assert "GLAC_REWRITE_DATA_FILES__WHERE" not in env_names
