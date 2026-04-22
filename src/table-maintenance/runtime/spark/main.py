"""Run an Iceberg table maintenance job via Spark SQL."""

from configs import JobSettings
from pyspark.sql import SparkSession
from sql_builder import IcebergCallBuilder


def main():
    """Build and execute the Iceberg maintenance SQL call."""
    settings = JobSettings()  # ty: ignore[missing-argument]
    print(f"Settings: {settings.model_dump_json(indent=2)}")

    sql = IcebergCallBuilder(settings).build_sql()
    print(f"SQL: {sql}")

    spark = SparkSession.builder.getOrCreate()
    result = spark.sql(sql)
    result.show(truncate=False)


if __name__ == "__main__":
    main()
