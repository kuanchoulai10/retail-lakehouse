"""Test the Spark configuration in the SparkApplication manifest."""

from __future__ import annotations

from dataclasses import replace

from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s import (
    SparkK8sConfig,
    build_spark_application,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    SubmitMaintenanceJobGatewayInput,
)

CONFIG = SparkK8sConfig(
    image="table-maintenance-spark:dev",
    service_account="spark",
    catalog_uri="http://polaris.lakehouse-catalog.svc:8181/api/catalog",
    catalog_credential_secret="polaris-spark-credential",
    s3_endpoint="http://rustfs.object-storage.svc:9000",
    s3_secret_name="rustfs-credentials",
)

INPUT = SubmitMaintenanceJobGatewayInput(
    run_id="run1",
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
