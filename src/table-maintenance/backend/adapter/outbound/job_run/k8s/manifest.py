"""Provide the build_manifest helper for Kubernetes job manifests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from adapter.outbound.job_run.k8s.constants import JOB_LABEL

if TYPE_CHECKING:
    from adapter.outbound.job_run.k8s.k8s_executor_config import K8sExecutorConfig
    from application.port.outbound.job_run.submit_job_run.input import (
        SubmitJobRunGatewayInput,
    )

_JOB_PREFIX: dict[str, str] = {
    "expire_snapshots": "GLAC_EXPIRE_SNAPSHOTS",
    "remove_orphan_files": "GLAC_REMOVE_ORPHAN_FILES",
    "rewrite_data_files": "GLAC_REWRITE_DATA_FILES",
    "rewrite_manifests": "GLAC_REWRITE_MANIFESTS",
}

_AWS_ENV = [
    {"name": "AWS_ACCESS_KEY_ID", "value": "minio_user"},
    {"name": "AWS_SECRET_ACCESS_KEY", "value": "minio_password"},
    {"name": "AWS_REGION", "value": "dummy-region"},
]


def _dict_to_env(prefix: str, config: dict) -> list[dict]:
    result = []
    for field_name, value in config.items():
        if value is None:
            continue
        env_key = f"{prefix}__{field_name.upper()}"
        env_val = str(value).lower() if isinstance(value, bool) else str(value)
        result.append({"name": env_key, "value": env_val})
    return result


def _build_driver_env(submission: SubmitJobRunGatewayInput) -> list[dict]:
    env = [
        {"name": "GLAC_JOB_TYPE", "value": submission.job_type},
        {"name": "GLAC_CATALOG", "value": submission.catalog},
    ]
    prefix = _JOB_PREFIX[submission.job_type]
    if submission.job_config:
        env.extend(_dict_to_env(prefix, submission.job_config))
    env.extend(_AWS_ENV)
    return env


def _build_spark_app_spec(
    submission: SubmitJobRunGatewayInput, config: K8sExecutorConfig, env: list[dict]
) -> dict:
    return {
        "type": "Python",
        "pythonVersion": "3",
        "mode": "cluster",
        "image": config.image,
        "imagePullPolicy": config.image_pull_policy,
        "mainApplicationFile": "local:///opt/spark/work-dir/main.py",
        "sparkVersion": config.spark_version,
        "deps": {
            "jars": [config.iceberg_jar, config.iceberg_aws_jar],
        },
        "sparkConf": {
            "spark.sql.extensions": "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
            "spark.driver.extraJavaOptions": "-Divy.cache.dir=/tmp/.ivy2 -Divy.home=/tmp/.ivy",
        },
        "driver": {
            "cores": 1,
            "memory": submission.driver_memory,
            "serviceAccount": config.service_account,
            "env": env,
        },
        "executor": {
            "cores": 1,
            "instances": submission.executor_instances,
            "memory": submission.executor_memory,
            "env": _AWS_ENV,
        },
    }


def build_manifest(
    submission: SubmitJobRunGatewayInput, config: K8sExecutorConfig
) -> dict:
    """Build a K8s manifest for a Spark job.

    Per-job values (memory, instances, job_config) come from the submission.
    System values (image, namespace, spark_version) come from the config.
    """
    env = _build_driver_env(submission)
    spark_spec = _build_spark_app_spec(submission, config, env)
    labels = {JOB_LABEL: submission.job_id}

    if submission.cron_expression:
        return {
            "apiVersion": "sparkoperator.k8s.io/v1beta2",
            "kind": "ScheduledSparkApplication",
            "metadata": {
                "name": submission.run_id,
                "namespace": config.namespace,
                "labels": labels,
            },
            "spec": {
                "schedule": submission.cron_expression,
                "template": spark_spec,
            },
        }

    return {
        "apiVersion": "sparkoperator.k8s.io/v1beta2",
        "kind": "SparkApplication",
        "metadata": {
            "name": submission.run_id,
            "namespace": config.namespace,
            "labels": labels,
        },
        "spec": spark_spec,
    }
