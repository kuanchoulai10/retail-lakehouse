from datetime import UTC, datetime

from config import AppSettings
from configs.base import JobType
from configs.jobs.expire_snapshots import ExpireSnapshotsConfig
from configs.jobs.rewrite_data_files import RewriteDataFilesConfig, Strategy
from k8s.manifest import build_manifest
from models.job_request import JobRequest

SETTINGS = AppSettings()


def _make_rewrite_request(**kwargs) -> JobRequest:
    return JobRequest(
        job_type=JobType.REWRITE_DATA_FILES,
        catalog="retail",
        spark_conf={"spark.sql.catalog.retail.uri": "http://polaris:8181/api/catalog"},
        rewrite_data_files=RewriteDataFilesConfig(table="inventory.orders", **kwargs),
    )


def test_kind_is_spark_application_without_cron():
    manifest = build_manifest("my-job", _make_rewrite_request(), SETTINGS)
    assert manifest["kind"] == "SparkApplication"
    assert manifest["apiVersion"] == "sparkoperator.k8s.io/v1beta2"


def test_name_and_namespace():
    manifest = build_manifest("my-job-abc123", _make_rewrite_request(), SETTINGS)
    assert manifest["metadata"]["name"] == "my-job-abc123"
    assert manifest["metadata"]["namespace"] == SETTINGS.namespace


def test_spark_conf_mapped():
    manifest = build_manifest("my-job", _make_rewrite_request(), SETTINGS)
    assert manifest["spec"]["sparkConf"]["spark.sql.catalog.retail.uri"] == "http://polaris:8181/api/catalog"


def test_driver_env_glac_vars():
    manifest = build_manifest("my-job", _make_rewrite_request(rewrite_all=True), SETTINGS)
    env = {e["name"]: e["value"] for e in manifest["spec"]["driver"]["env"]}
    assert env["GLAC_JOB_TYPE"] == "rewrite_data_files"
    assert env["GLAC_CATALOG"] == "retail"
    assert env["GLAC_REWRITE_DATA_FILES__TABLE"] == "inventory.orders"
    assert env["GLAC_REWRITE_DATA_FILES__REWRITE_ALL"] == "true"


def test_strategy_enum_serialized_as_value():
    req = _make_rewrite_request(strategy=Strategy.SORT)
    manifest = build_manifest("my-job", req, SETTINGS)
    env = {e["name"]: e["value"] for e in manifest["spec"]["driver"]["env"]}
    assert env["GLAC_REWRITE_DATA_FILES__STRATEGY"] == "sort"


def test_expire_snapshots_datetime_env():
    dt = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    req = JobRequest(
        job_type=JobType.EXPIRE_SNAPSHOTS,
        catalog="retail",
        spark_conf={},
        expire_snapshots=ExpireSnapshotsConfig(table="inventory.orders", older_than=dt),
    )
    manifest = build_manifest("my-job", req, SETTINGS)
    env = {e["name"]: e["value"] for e in manifest["spec"]["driver"]["env"]}
    assert env["GLAC_EXPIRE_SNAPSHOTS__TABLE"] == "inventory.orders"
    assert "2026-01-01" in env["GLAC_EXPIRE_SNAPSHOTS__OLDER_THAN"]


def test_executor_env_has_aws_vars():
    manifest = build_manifest("my-job", _make_rewrite_request(), SETTINGS)
    exec_env_keys = {e["name"] for e in manifest["spec"]["executor"]["env"]}
    assert "AWS_ACCESS_KEY_ID" in exec_env_keys
    assert "AWS_SECRET_ACCESS_KEY" in exec_env_keys


def test_resource_overrides():
    req = _make_rewrite_request()
    req.driver_memory = "1g"
    req.executor_memory = "2g"
    req.executor_instances = 2
    manifest = build_manifest("my-job", req, SETTINGS)
    assert manifest["spec"]["driver"]["memory"] == "1g"
    assert manifest["spec"]["executor"]["memory"] == "2g"
    assert manifest["spec"]["executor"]["instances"] == 2


def test_cron_creates_scheduled_spark_application():
    req = _make_rewrite_request()
    req.cron = "0 2 * * *"
    manifest = build_manifest("my-job", req, SETTINGS)
    assert manifest["kind"] == "ScheduledSparkApplication"
    assert manifest["spec"]["schedule"] == "0 2 * * *"
    assert "type" in manifest["spec"]["template"]


def test_none_fields_not_in_env():
    req = _make_rewrite_request()
    manifest = build_manifest("my-job", req, SETTINGS)
    env_names = {e["name"] for e in manifest["spec"]["driver"]["env"]}
    assert "GLAC_REWRITE_DATA_FILES__SORT_ORDER" not in env_names
    assert "GLAC_REWRITE_DATA_FILES__WHERE" not in env_names
