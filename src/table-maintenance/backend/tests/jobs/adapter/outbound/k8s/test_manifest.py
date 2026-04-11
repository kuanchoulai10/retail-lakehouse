from datetime import UTC, datetime

from jobs.adapter.outbound.k8s.manifest import build_manifest
from jobs.application.domain.model.job import Job
from jobs.application.domain.model.job_id import JobId
from jobs.application.domain.model.job_status import JobStatus
from jobs.application.domain.model.job_type import JobType
from jobs.application.port.inbound.create_job.input import CreateJobInput
from shared.configs import AppSettings

SETTINGS = AppSettings()


def _make_job(name: str = "my-job") -> Job:
    return Job(
        id=JobId(value=name),
        job_type=JobType.REWRITE_DATA_FILES,
        status=JobStatus.PENDING,
        created_at=datetime.now(UTC),
    )


def _make_rewrite_input(**kwargs) -> CreateJobInput:
    return CreateJobInput(
        job_type="rewrite_data_files",
        catalog="retail",
        spark_conf={"spark.sql.catalog.retail.uri": "http://polaris:8181/api/catalog"},
        rewrite_data_files={"table": "inventory.orders", **kwargs},
    )


def test_kind_is_spark_application_without_cron():
    manifest = build_manifest(_make_job(), SETTINGS, _make_rewrite_input())
    assert manifest["kind"] == "SparkApplication"
    assert manifest["apiVersion"] == "sparkoperator.k8s.io/v1beta2"


def test_name_and_namespace():
    manifest = build_manifest(_make_job("my-job-abc123"), SETTINGS, _make_rewrite_input())
    assert manifest["metadata"]["name"] == "my-job-abc123"
    assert manifest["metadata"]["namespace"] == SETTINGS.namespace


def test_spark_conf_mapped():
    manifest = build_manifest(_make_job(), SETTINGS, _make_rewrite_input())
    assert manifest["spec"]["sparkConf"]["spark.sql.catalog.retail.uri"] == "http://polaris:8181/api/catalog"


def test_driver_env_glac_vars():
    manifest = build_manifest(_make_job(), SETTINGS, _make_rewrite_input(rewrite_all=True))
    env = {e["name"]: e["value"] for e in manifest["spec"]["driver"]["env"]}
    assert env["GLAC_JOB_TYPE"] == "rewrite_data_files"
    assert env["GLAC_CATALOG"] == "retail"
    assert env["GLAC_REWRITE_DATA_FILES__TABLE"] == "inventory.orders"
    assert env["GLAC_REWRITE_DATA_FILES__REWRITE_ALL"] == "true"


def test_strategy_enum_serialized_as_value():
    input_ = _make_rewrite_input(strategy="sort")
    manifest = build_manifest(_make_job(), SETTINGS, input_)
    env = {e["name"]: e["value"] for e in manifest["spec"]["driver"]["env"]}
    assert env["GLAC_REWRITE_DATA_FILES__STRATEGY"] == "sort"


def test_expire_snapshots_datetime_env():
    dt = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    input_ = CreateJobInput(
        job_type="expire_snapshots",
        catalog="retail",
        spark_conf={},
        expire_snapshots={"table": "inventory.orders", "older_than": dt.isoformat()},
    )
    manifest = build_manifest(_make_job(), SETTINGS, input_)
    env = {e["name"]: e["value"] for e in manifest["spec"]["driver"]["env"]}
    assert env["GLAC_EXPIRE_SNAPSHOTS__TABLE"] == "inventory.orders"
    assert "2026-01-01" in env["GLAC_EXPIRE_SNAPSHOTS__OLDER_THAN"]


def test_executor_env_has_aws_vars():
    manifest = build_manifest(_make_job(), SETTINGS, _make_rewrite_input())
    exec_env_keys = {e["name"] for e in manifest["spec"]["executor"]["env"]}
    assert "AWS_ACCESS_KEY_ID" in exec_env_keys
    assert "AWS_SECRET_ACCESS_KEY" in exec_env_keys


def test_resource_overrides():
    input_ = CreateJobInput(
        job_type="rewrite_data_files",
        catalog="retail",
        spark_conf={},
        rewrite_data_files={"table": "inventory.orders"},
        driver_memory="1g",
        executor_memory="2g",
        executor_instances=2,
    )
    manifest = build_manifest(_make_job(), SETTINGS, input_)
    assert manifest["spec"]["driver"]["memory"] == "1g"
    assert manifest["spec"]["executor"]["memory"] == "2g"
    assert manifest["spec"]["executor"]["instances"] == 2


def test_cron_creates_scheduled_spark_application():
    input_ = CreateJobInput(
        job_type="rewrite_data_files",
        catalog="retail",
        spark_conf={},
        rewrite_data_files={"table": "inventory.orders"},
        cron="0 2 * * *",
    )
    manifest = build_manifest(_make_job(), SETTINGS, input_)
    assert manifest["kind"] == "ScheduledSparkApplication"
    assert manifest["spec"]["schedule"] == "0 2 * * *"
    assert "type" in manifest["spec"]["template"]


def test_none_fields_not_in_env():
    manifest = build_manifest(_make_job(), SETTINGS, _make_rewrite_input())
    env_names = {e["name"] for e in manifest["spec"]["driver"]["env"]}
    assert "GLAC_REWRITE_DATA_FILES__SORT_ORDER" not in env_names
    assert "GLAC_REWRITE_DATA_FILES__WHERE" not in env_names
