"""Test the Spark configuration in the SparkApplication manifest."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s import (
    SparkK8sConfig,
    SparkSizeResources,
    VolcanoSettings,
    build_spark_application,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    SubmitMaintenanceJobGatewayInput,
)

RUN_1 = "mr-00000000000000000000000001"

CONFIG = SparkK8sConfig(
    image="table-maintenance-spark:dev",
    service_account="spark",
    catalog_uri="http://polaris.lakehouse-catalog.svc:8181/api/catalog",
    catalog_credential_secret="polaris-spark-credential",
    s3_endpoint="http://rustfs.object-storage.svc:9000",
    s3_secret_name="rustfs-credentials",
)

INPUT = SubmitMaintenanceJobGatewayInput(
    run_id=RUN_1,
    operation="rewrite_data_files",
    attempt=1,
    catalog="iceberg",
    namespace="sales",
    table="orders",
    where=[],
    procedure_args={},
    callback_url="http://cp/callback",
)

HADOOP_MAVEN = "https://repo1.maven.org/maven2/org/apache/hadoop"
AWS_SDK_MAVEN = "https://repo1.maven.org/maven2/software/amazon/awssdk"


def _spec(config: SparkK8sConfig = CONFIG) -> dict:
    return build_spark_application(config, INPUT, "app")["spec"]


def test_spark_application_enables_compressed_rolling_event_log():
    """The manifest enables a compressed event log in the configured bucket."""
    spec = _spec()

    conf = spec["sparkConf"]
    assert conf["spark.eventLog.enabled"] == "true"
    assert conf["spark.eventLog.dir"] == "s3a://spark-event-logs/"
    assert conf["spark.eventLog.compress"] == "true"
    assert conf["spark.eventLog.compression.codec"] == "zstd"
    assert conf["spark.eventLog.logStageExecutorMetrics"] == "true"
    assert conf["spark.eventLog.rolling.enabled"] == "true"
    assert conf["spark.eventLog.rolling.maxFileSize"] == "128m"
    assert conf["spark.hadoop.fs.s3a.endpoint"] == CONFIG.s3_endpoint
    assert conf["spark.hadoop.fs.s3a.path.style.access"] == "true"
    assert f"{HADOOP_MAVEN}/hadoop-aws/3.4.1/hadoop-aws-3.4.1.jar" in spec["deps"]["jars"]


def test_spark_application_event_log_dir_is_configurable():
    """The event log directory comes from the config."""
    spec = _spec(replace(CONFIG, event_log_dir="s3a://other-logs/"))

    assert spec["sparkConf"]["spark.eventLog.dir"] == "s3a://other-logs/"


def test_spark_application_s3a_reads_credentials_from_the_secret_env():
    """S3A reads its credentials from the secret environment and uses the configured region."""
    conf = _spec()["sparkConf"]

    assert conf["spark.hadoop.fs.s3a.aws.credentials.provider"] == (
        "software.amazon.awssdk.auth.credentials.EnvironmentVariableCredentialsProvider"
    )
    assert conf["spark.hadoop.fs.s3a.endpoint.region"] == CONFIG.s3_region


def test_spark_application_s3a_ssl_follows_the_endpoint_scheme():
    """S3A SSL is off for an http endpoint and on for an https endpoint."""
    http_conf = _spec()["sparkConf"]
    https_conf = _spec(replace(CONFIG, s3_endpoint="https://s3.example.com"))["sparkConf"]

    assert http_conf["spark.hadoop.fs.s3a.connection.ssl.enabled"] == "false"
    assert https_conf["spark.hadoop.fs.s3a.connection.ssl.enabled"] == "true"


def test_spark_application_s3a_path_style_follows_the_config():
    """S3A path style access follows the config."""
    conf = _spec(replace(CONFIG, s3_path_style_access=False))["sparkConf"]

    assert conf["spark.hadoop.fs.s3a.path.style.access"] == "false"


def test_spark_application_adds_the_s3_transfer_manager_matching_the_iceberg_sdk():
    """The manifest adds the S3 transfer manager jar that matches the AWS SDK of Iceberg."""
    jars = _spec()["deps"]["jars"]

    assert f"{AWS_SDK_MAVEN}/s3-transfer-manager/2.33.0/s3-transfer-manager-2.33.0.jar" in jars


def test_spark_application_pins_hadoop_and_sdk_versions_from_the_config():
    """The Hadoop and AWS SDK jar versions come from the config."""
    jars = _spec(replace(CONFIG, hadoop_version="3.4.2", aws_sdk_version="2.34.0"))["deps"]["jars"]

    assert f"{HADOOP_MAVEN}/hadoop-aws/3.4.2/hadoop-aws-3.4.2.jar" in jars
    assert f"{AWS_SDK_MAVEN}/s3-transfer-manager/2.34.0/s3-transfer-manager-2.34.0.jar" in jars


def test_spark_application_caps_driver_and_executor_cpu_at_one_core():
    """By default the driver and executor pods may use at most one core each."""
    spec = _spec()

    assert spec["driver"]["coreLimit"] == "1"
    assert spec["executor"]["coreLimit"] == "1"


def test_spark_application_core_limits_are_configurable():
    """The driver and executor CPU limits come from the config."""
    spec = _spec(replace(CONFIG, driver_core_limit="1500m", executor_core_limit="2"))

    assert spec["driver"]["coreLimit"] == "1500m"
    assert spec["executor"]["coreLimit"] == "2"


def test_spark_application_labels_driver_and_executor_pods_with_the_attempt():
    """The driver and executor pods carry the run, operation and attempt, so one attempt's pods can be found."""
    spec = _spec()

    attempt_labels = {
        "table-maintenance/run-id": RUN_1,
        "table-maintenance/operation": "rewrite_data_files",
        "table-maintenance/attempt": "1",
    }
    assert spec["driver"]["labels"] == attempt_labels
    assert spec["executor"]["labels"] == attempt_labels


@pytest.mark.parametrize(
    ("size", "driver", "executor"),
    [("S", "768m", "768m"), ("M", "1g", "1536m"), ("L", "1536m", "2g")],
)
def test_manifest_uses_the_memory_of_the_attempt_size(size: str, driver: str, executor: str):
    """The driver and executor memory and the executor count come from the attempt's size."""
    spec = build_spark_application(CONFIG, replace(INPUT, size=size), "app")["spec"]

    assert spec["driver"]["memory"] == driver
    assert spec["executor"]["memory"] == executor
    assert spec["executor"]["instances"] == 1


def test_manifest_keeps_one_core():
    """Every size keeps one core and a one-core limit for the driver and executor."""
    for size in ("S", "M", "L"):
        spec = build_spark_application(CONFIG, replace(INPUT, size=size), "app")["spec"]
        assert (spec["driver"]["cores"], spec["driver"]["coreLimit"]) == (1, "1")
        assert (spec["executor"]["cores"], spec["executor"]["coreLimit"]) == (1, "1")


def test_configured_size_resources_are_used():
    """A size configured with other resources renders them."""
    config = replace(
        CONFIG, sizes={"S": SparkSizeResources(driver_memory="1g", executor_memory="3g", executor_instances=2)}
    )
    spec = build_spark_application(config, INPUT, "app")["spec"]
    assert (spec["driver"]["memory"], spec["executor"]["memory"], spec["executor"]["instances"]) == ("1g", "3g", 2)


def test_unknown_size_is_refused():
    """A size the config does not define is refused, naming it."""
    with pytest.raises(ValueError, match="XL"):
        build_spark_application(CONFIG, replace(INPUT, size="XL"), "app")


def test_executor_pods_are_kept_after_they_end():
    """Ended executor pods stay, with their exit status, until the application is deleted."""
    assert _spec()["sparkConf"]["spark.kubernetes.executor.deleteOnTermination"] == "false"


def test_driver_falls_back_to_its_log_for_the_termination_message():
    """A driver that dies with an error carries the tail of its log as its termination message."""
    assert _spec()["driver"]["template"] == {
        "spec": {
            "containers": [
                {"name": "spark-kubernetes-driver", "terminationMessagePolicy": "FallbackToLogsOnError"},
            ]
        }
    }


def test_the_job_request_carries_the_size():
    """The runtime's request names the attempt's size."""
    env = {e["name"]: e.get("value") for e in _spec()["driver"]["env"]}
    assert json.loads(env["GLAC_REQUEST"])["size"] == "S"


def test_manifest_uses_volcano_for_p0():
    """A P0 job goes to the urgent queue, in the P0 class, with its resources spelled out."""
    spec = build_spark_application(CONFIG, replace(INPUT, priority="P0"), "app")["spec"]

    assert spec["batchScheduler"] == "volcano"
    assert spec["batchSchedulerOptions"] == {
        "queue": "table-maintenance-urgent",
        "priorityClassName": "table-maintenance-p0",
        "resources": {"cpu": "2", "memory": "2304Mi"},
    }


def test_manifest_puts_p3_in_the_normal_queue():
    """A P3 job goes to the normal queue in the P3 class."""
    options = build_spark_application(CONFIG, replace(INPUT, priority="P3"), "app")["spec"]["batchSchedulerOptions"]

    assert (options["queue"], options["priorityClassName"]) == ("table-maintenance", "table-maintenance-p3")


def test_manifest_defaults_to_p3():
    """An input without a priority is scheduled as P3."""
    options = _spec()["batchSchedulerOptions"]

    assert (options["queue"], options["priorityClassName"]) == ("table-maintenance", "table-maintenance-p3")


def test_pod_group_resources_follow_the_size_and_the_cores():
    """The PodGroup holds the memory of the attempt's size and the configured cores."""
    spec = build_spark_application(replace(CONFIG, driver_cores=2), replace(INPUT, size="L"), "app")["spec"]

    assert spec["batchSchedulerOptions"]["resources"] == {"cpu": "3", "memory": "5017Mi"}


def test_volcano_names_are_configurable():
    """The queue names and the class prefix come from the config."""
    config = replace(CONFIG, volcano=VolcanoSettings(queue="q", urgent_queue="uq", priority_class_prefix="pc"))

    options = build_spark_application(config, replace(INPUT, priority="P0"), "app")["spec"]["batchSchedulerOptions"]

    assert (options["queue"], options["priorityClassName"]) == ("uq", "pc-p0")


def test_the_job_request_carries_the_priority():
    """The runtime's request names the run's priority."""
    spec = build_spark_application(CONFIG, replace(INPUT, priority="P1"), "app")["spec"]
    env = {e["name"]: e.get("value") for e in spec["driver"]["env"]}

    assert json.loads(env["GLAC_REQUEST"])["priority"] == "P1"
