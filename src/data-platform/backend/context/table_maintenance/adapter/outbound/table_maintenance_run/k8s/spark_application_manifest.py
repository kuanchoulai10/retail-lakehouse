"""Define the build_spark_application function."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s.iceberg_procedure_args import (
    iceberg_procedure_args,
)
from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s.maintenance_job_pod_labels import (
    maintenance_job_pod_labels,
)
from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s.pod_group_resources import (
    pod_group_resources,
)
from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s.spark_where_clauses import (
    spark_where_clauses,
)

if TYPE_CHECKING:
    from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s.spark_k8s_config import (
        SparkK8sConfig,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_run import (
        SubmitMaintenanceJobGatewayInput,
    )

GROUP = "sparkoperator.k8s.io"
VERSION = "v1beta2"
PLURAL = "sparkapplications"
ICEBERG_EXTENSIONS = "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions"
MAVEN = "https://repo1.maven.org/maven2/org/apache/iceberg"
HADOOP_MAVEN = "https://repo1.maven.org/maven2/org/apache/hadoop"
AWS_SDK_MAVEN = "https://repo1.maven.org/maven2/software/amazon/awssdk"
ENV_CREDENTIALS_PROVIDER = "software.amazon.awssdk.auth.credentials.EnvironmentVariableCredentialsProvider"
REDACTION_REGEX = "(?i)secret|password|token|credential"
IVY_OPTIONS = "-Divy.cache.dir=/tmp/.ivy2 -Divy.home=/tmp/.ivy"
_DRIVER_CONTAINER = "spark-kubernetes-driver"


def _jars(config: SparkK8sConfig) -> list[str]:
    version = config.iceberg_version
    return [
        f"{MAVEN}/iceberg-spark-runtime-4.0_2.13/{version}/iceberg-spark-runtime-4.0_2.13-{version}.jar",
        f"{MAVEN}/iceberg-aws-bundle/{version}/iceberg-aws-bundle-{version}.jar",
        f"{HADOOP_MAVEN}/hadoop-aws/{config.hadoop_version}/hadoop-aws-{config.hadoop_version}.jar",
        f"{AWS_SDK_MAVEN}/s3-transfer-manager/{config.aws_sdk_version}/"
        f"s3-transfer-manager-{config.aws_sdk_version}.jar",
    ]


def _event_log_conf(config: SparkK8sConfig) -> dict[str, str]:
    return {
        "spark.eventLog.enabled": "true",
        "spark.eventLog.dir": config.event_log_dir,
        "spark.eventLog.compress": "true",
        "spark.eventLog.compression.codec": "zstd",
        "spark.eventLog.logStageExecutorMetrics": "true",
        "spark.eventLog.rolling.enabled": "true",
        "spark.eventLog.rolling.maxFileSize": "128m",
    }


def _s3a_conf(config: SparkK8sConfig) -> dict[str, str]:
    ssl = not config.s3_endpoint.startswith("http://")
    return {
        "spark.hadoop.fs.s3a.endpoint": config.s3_endpoint,
        "spark.hadoop.fs.s3a.endpoint.region": config.s3_region,
        "spark.hadoop.fs.s3a.path.style.access": str(config.s3_path_style_access).lower(),
        "spark.hadoop.fs.s3a.connection.ssl.enabled": str(ssl).lower(),
        "spark.hadoop.fs.s3a.aws.credentials.provider": ENV_CREDENTIALS_PROVIDER,
    }


def _spark_conf(
    config: SparkK8sConfig,
    input: SubmitMaintenanceJobGatewayInput,  # noqa: A002
) -> dict[str, str]:
    prefix = f"spark.sql.catalog.{input.catalog}"
    return {
        "spark.sql.extensions": ICEBERG_EXTENSIONS,
        "spark.sql.session.timeZone": "UTC",
        "spark.redaction.regex": REDACTION_REGEX,
        prefix: "org.apache.iceberg.spark.SparkCatalog",
        f"{prefix}.type": "rest",
        f"{prefix}.uri": config.catalog_uri,
        f"{prefix}.warehouse": input.catalog,
        f"{prefix}.scope": config.catalog_scope,
        f"{prefix}.io-impl": "org.apache.iceberg.aws.s3.S3FileIO",
        f"{prefix}.s3.endpoint": config.s3_endpoint,
        f"{prefix}.s3.path-style-access": str(config.s3_path_style_access).lower(),
        **_event_log_conf(config),
        **_s3a_conf(config),
        **_executor_conf(),
    }


def _executor_conf() -> dict[str, str]:
    """Keep ended executor pods, with their exit status, until their application is deleted."""
    return {"spark.kubernetes.executor.deleteOnTermination": "false"}


def _spark_request(input: SubmitMaintenanceJobGatewayInput, name: str) -> dict[str, Any]:  # noqa: A002
    """Return the request the Spark runtime reads: the table, the ``CALL``'s where clauses and arguments.

    The keys and their order are the runtime's contract; ``where`` and ``procedure_args`` are the job
    written in Iceberg's spelling.
    """
    return {
        "run_id": input.run_id,
        "operation": input.operation,
        "attempt": input.attempt,
        "catalog": input.catalog,
        "namespace": input.namespace,
        "table": input.table,
        "where": spark_where_clauses(input.catalog, input.job),
        "procedure_args": iceberg_procedure_args(input.job),
        "result_report_url": input.result_report_url,
        "size": input.size,
        "priority": input.priority,
        "app_name": name,
    }


def build_spark_application(
    config: SparkK8sConfig,
    input: SubmitMaintenanceJobGatewayInput,  # noqa: A002
    name: str,
) -> dict[str, Any]:
    """Render the SparkApplication custom resource named ``name`` of one job.

    The driver and executor pods carry the same run, operation and attempt labels
    as the application, so the pods of one attempt can be found after it is deleted.
    Their memory and the executor count come from the attempt's size; a driver that
    dies with an error carries the tail of its log as its termination message.
    The application is scheduled by Volcano in the queue and priority class of the run's
    priority, with the PodGroup's cpu and memory spelled out, because the operator's own
    arithmetic cannot read Spark memory strings. Only the PodGroup carries the class: the
    pods keep none, so under memory pressure they are not evicted after platform services.
    """
    resources = config.sizes.get(input.size)
    if resources is None:
        msg = f"unknown Spark size {input.size!r}; known sizes: {', '.join(config.sizes)}"
        raise ValueError(msg)
    s3_env_from = [{"secretRef": {"name": config.s3_secret_name}}]
    attempt_labels = maintenance_job_pod_labels(input.run_id, input.operation, input.attempt)
    region_env = {"name": "AWS_REGION", "value": config.s3_region}
    return {
        "apiVersion": f"{GROUP}/{VERSION}",
        "kind": "SparkApplication",
        "metadata": {
            "name": name,
            "namespace": config.namespace,
            "labels": {
                "app.kubernetes.io/part-of": "table-maintenance",
                **attempt_labels,
            },
        },
        "spec": {
            "type": "Python",
            "mode": "cluster",
            "image": config.image,
            "imagePullPolicy": config.image_pull_policy,
            "sparkVersion": config.spark_version,
            "mainApplicationFile": config.main_application_file,
            "restartPolicy": {"type": "Never"},
            "batchScheduler": "volcano",
            "batchSchedulerOptions": {
                "queue": config.volcano.queue_for(input.priority),
                "priorityClassName": config.volcano.priority_class_for(input.priority),
                "resources": pod_group_resources(resources, config.driver_cores, config.executor_cores),
            },
            "deps": {"jars": _jars(config)},
            "sparkConf": _spark_conf(config, input),
            "driver": {
                "labels": dict(attempt_labels),
                "cores": config.driver_cores,
                "coreLimit": config.driver_core_limit,
                "memory": resources.driver_memory,
                "serviceAccount": config.service_account,
                "template": {
                    "spec": {
                        "containers": [
                            {"name": _DRIVER_CONTAINER, "terminationMessagePolicy": "FallbackToLogsOnError"},
                        ]
                    }
                },
                "javaOptions": IVY_OPTIONS,
                "envFrom": s3_env_from,
                "env": [
                    {
                        "name": "GLAC_REQUEST",
                        "value": json.dumps(_spark_request(input, name)),
                    },
                    {
                        "name": "POLARIS_CREDENTIAL",
                        "valueFrom": {
                            "secretKeyRef": {
                                "name": config.catalog_credential_secret,
                                "key": "credential",
                            }
                        },
                    },
                    region_env,
                ],
            },
            "executor": {
                "labels": dict(attempt_labels),
                "instances": resources.executor_instances,
                "cores": config.executor_cores,
                "coreLimit": config.executor_core_limit,
                "memory": resources.executor_memory,
                "javaOptions": IVY_OPTIONS,
                "envFrom": s3_env_from,
                "env": [region_env],
            },
        },
    }
