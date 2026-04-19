"""Run an Iceberg table maintenance job via Spark SQL."""

from configs import JobSettings
from pyspark.sql import SparkSession
from sql_builder import IcebergCallBuilder


def main():
    """Build and execute the Iceberg maintenance SQL call."""
    settings = JobSettings()  # ty: ignore[missing-argument]
    sql = IcebergCallBuilder(settings).build_sql()

    spark = SparkSession.builder.getOrCreate()
    spark.sql(sql)


if __name__ == "__main__":
    main()
