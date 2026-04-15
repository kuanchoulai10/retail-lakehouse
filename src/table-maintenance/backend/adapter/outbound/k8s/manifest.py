from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from configs import AppSettings

    from application.domain.model.job import Job

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


def _build_driver_env(job: Job) -> list[dict]:
    job_type = job.job_type.value
    env = [
        {"name": "GLAC_JOB_TYPE", "value": job_type},
        {"name": "GLAC_CATALOG", "value": job.catalog},
    ]
    prefix = _JOB_PREFIX[job_type]
    if job.job_config:
        env.extend(_dict_to_env(prefix, job.job_config))
    env.extend(_AWS_ENV)
    return env


def _build_spark_app_spec(job: Job, settings: AppSettings, env: list[dict]) -> dict:
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
            "spark.sql.extensions": "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
            "spark.driver.extraJavaOptions": "-Divy.cache.dir=/tmp/.ivy2 -Divy.home=/tmp/.ivy",
        },
        "driver": {
            "cores": 1,
            "memory": settings.driver_memory,
            "serviceAccount": settings.service_account,
            "env": env,
        },
        "executor": {
            "cores": 1,
            "instances": settings.executor_instances,
            "memory": settings.executor_memory,
            "env": _AWS_ENV,
        },
    }


def build_manifest(job: Job, settings: AppSettings) -> dict:
    name = job.id.value
    env = _build_driver_env(job)
    spark_spec = _build_spark_app_spec(job, settings, env)

    if job.cron:
        return {
            "apiVersion": "sparkoperator.k8s.io/v1beta2",
            "kind": "ScheduledSparkApplication",
            "metadata": {"name": name, "namespace": settings.namespace},
            "spec": {
                "schedule": job.cron,
                "template": spark_spec,
            },
        }

    return {
        "apiVersion": "sparkoperator.k8s.io/v1beta2",
        "kind": "SparkApplication",
        "metadata": {"name": name, "namespace": settings.namespace},
        "spec": spark_spec,
    }
