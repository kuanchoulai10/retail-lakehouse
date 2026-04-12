from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BACKEND_")

    namespace: str = "default"
    image: str = "localhost:5000/table-maintenance-jobs:latest"
    image_pull_policy: str = "Never"
    spark_version: str = "4.0.0"
    service_account: str = "spark-operator-spark"
    iceberg_jar: str = (
        "https://repo1.maven.org/maven2/org/apache/iceberg/"
        "iceberg-spark-runtime-4.0_2.13/1.10.1/"
        "iceberg-spark-runtime-4.0_2.13-1.10.1.jar"
    )
    iceberg_aws_jar: str = (
        "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-aws-bundle/1.10.1/iceberg-aws-bundle-1.10.1.jar"
    )
    driver_memory: str = "512m"
    executor_memory: str = "1g"
    executor_instances: int = 1
