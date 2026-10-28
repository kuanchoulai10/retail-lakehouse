"""Define the build_spark_application function."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from adapter.outbound.table_maintenance_run.k8s.spark_k8s_config import (
        SparkK8sConfig,
    )
    from application.port.outbound.table_maintenance_run import (
        SubmitMaintenanceJobGatewayInput,
    )

GROUP = "sparkoperator.k8s.io"
VERSION = "v1beta2"
PLURAL = "sparkapplications"
ICEBERG_EXTENSIONS = "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions"
MAVEN = "https://repo1.maven.org/maven2/org/apache/iceberg"
REDACTION_REGEX = "(?i)secret|password|token|credential"
IVY_OPTIONS = "-Divy.cache.dir=/tmp/.ivy2 -Divy.home=/tmp/.ivy"


def _jars(config: SparkK8sConfig) -> list[str]:
    version = config.iceberg_version
    return [
        f"{MAVEN}/iceberg-spark-runtime-4.0_2.13/{version}/"
        f"iceberg-spark-runtime-4.0_2.13-{version}.jar",
        f"{MAVEN}/iceberg-aws-bundle/{version}/iceberg-aws-bundle-{version}.jar",
    ]


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
    }


def build_spark_application(
    config: SparkK8sConfig,
    input: SubmitMaintenanceJobGatewayInput,  # noqa: A002
    name: str,
) -> dict[str, Any]:
    """Render the SparkApplication custom resource named ``name`` of one job."""
    s3_env_from = [{"secretRef": {"name": config.s3_secret_name}}]
    region_env = {"name": "AWS_REGION", "value": config.s3_region}
    return {
        "apiVersion": f"{GROUP}/{VERSION}",
        "kind": "SparkApplication",
        "metadata": {
            "name": name,
            "namespace": config.namespace,
            "labels": {
                "app.kubernetes.io/part-of": "table-maintenance",
                "table-maintenance/run-id": input.run_id,
                "table-maintenance/operation": input.operation,
                "table-maintenance/attempt": str(input.attempt),
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
            "deps": {"jars": _jars(config)},
            "sparkConf": _spark_conf(config, input),
            "driver": {
                "cores": config.driver_cores,
                "memory": config.driver_memory,
                "serviceAccount": config.service_account,
                "javaOptions": IVY_OPTIONS,
                "envFrom": s3_env_from,
                "env": [
                    {
                        "name": "GLAC_REQUEST",
                        "value": json.dumps({**asdict(input), "app_name": name}),
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
                "instances": config.executor_instances,
                "cores": config.executor_cores,
                "memory": config.executor_memory,
                "javaOptions": IVY_OPTIONS,
                "envFrom": s3_env_from,
                "env": [region_env],
            },
        },
    }
