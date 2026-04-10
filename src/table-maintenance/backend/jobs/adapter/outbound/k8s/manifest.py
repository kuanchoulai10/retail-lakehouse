from __future__ import annotations

from typing import TYPE_CHECKING

from jobs.domain.job_type import JobType

if TYPE_CHECKING:
    from pydantic import BaseModel
    from shared.configs import AppSettings

    from jobs.adapter.inbound.web.dto import JobRequest

_JOB_PREFIX: dict[JobType, str] = {
    JobType.EXPIRE_SNAPSHOTS: "GLAC_EXPIRE_SNAPSHOTS",
    JobType.REMOVE_ORPHAN_FILES: "GLAC_REMOVE_ORPHAN_FILES",
    JobType.REWRITE_DATA_FILES: "GLAC_REWRITE_DATA_FILES",
    JobType.REWRITE_MANIFESTS: "GLAC_REWRITE_MANIFESTS",
}

_AWS_ENV = [
    {"name": "AWS_ACCESS_KEY_ID", "value": "minio_user"},
    {"name": "AWS_SECRET_ACCESS_KEY", "value": "minio_password"},
    {"name": "AWS_REGION", "value": "dummy-region"},
]


def _model_to_env(prefix: str, model: BaseModel) -> list[dict]:
    result = []
    for field_name, value in model.model_dump(mode="json", exclude_none=True).items():
        env_key = f"{prefix}__{field_name.upper()}"
        env_val = str(value).lower() if isinstance(value, bool) else str(value)
        result.append({"name": env_key, "value": env_val})
    return result


def _build_driver_env(request: JobRequest) -> list[dict]:
    env = [
        {"name": "GLAC_JOB_TYPE", "value": request.job_type.value},
        {"name": "GLAC_CATALOG", "value": request.catalog},
    ]
    config_by_type = {
        JobType.EXPIRE_SNAPSHOTS: request.expire_snapshots,
        JobType.REMOVE_ORPHAN_FILES: request.remove_orphan_files,
        JobType.REWRITE_DATA_FILES: request.rewrite_data_files,
        JobType.REWRITE_MANIFESTS: request.rewrite_manifests,
    }
    prefix = _JOB_PREFIX[request.job_type]
    job_config = config_by_type[request.job_type]
    if job_config:
        env.extend(_model_to_env(prefix, job_config))
    env.extend(_AWS_ENV)
    return env


def _build_spark_app_spec(request: JobRequest, settings: AppSettings, env: list[dict]) -> dict:
    return {
        "type": "Python",
        "pythonVersion": "3",
        "mode": "cluster",
        "image": settings.image,
        "imagePullPolicy": settings.image_pull_policy,
        "mainApplicationFile": "local:///opt/spark/work-dir/main.py",
        "sparkVersion": settings.spark_version,
        "deps": {
            "jars": [settings.iceberg_jar, settings.iceberg_aws_jar],
        },
        "sparkConf": {
            "spark.sql.extensions": ("org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions"),
            "spark.driver.extraJavaOptions": ("-Divy.cache.dir=/tmp/.ivy2 -Divy.home=/tmp/.ivy"),
            **request.spark_conf,
        },
        "driver": {
            "cores": 1,
            "memory": request.driver_memory,
            "serviceAccount": settings.service_account,
            "env": env,
        },
        "executor": {
            "cores": 1,
            "instances": request.executor_instances,
            "memory": request.executor_memory,
            "env": _AWS_ENV,
        },
    }


def build_manifest(name: str, request: JobRequest, settings: AppSettings) -> dict:
    env = _build_driver_env(request)
    spark_spec = _build_spark_app_spec(request, settings, env)

    if request.cron:
        return {
            "apiVersion": "sparkoperator.k8s.io/v1beta2",
            "kind": "ScheduledSparkApplication",
            "metadata": {"name": name, "namespace": settings.namespace},
            "spec": {
                "schedule": request.cron,
                "template": spark_spec,
            },
        }

    return {
        "apiVersion": "sparkoperator.k8s.io/v1beta2",
        "kind": "SparkApplication",
        "metadata": {"name": name, "namespace": settings.namespace},
        "spec": spark_spec,
    }
