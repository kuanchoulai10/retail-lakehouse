"""Run planned Iceberg table maintenance on Spark and post a result callback.

A failure to parse GLAC_REQUEST or to build the Spark session exits non-zero without a
callback; the workflow then falls back to polling the SparkApplication state.
"""

from __future__ import annotations

import logging
import os
import sys

from job_request import JobRequest
from maintenance_runner import run_maintenance


def _session(catalog: str):
    from pyspark.sql import SparkSession

    builder = SparkSession.builder.config("spark.sql.session.timeZone", "UTC")
    credential = os.environ.get("POLARIS_CREDENTIAL")
    if credential:
        builder = builder.config(f"spark.sql.catalog.{catalog}.credential", credential)
    return builder.getOrCreate()


def main() -> int:
    """Parse GLAC_REQUEST, run the maintenance and return the exit code."""
    logging.basicConfig(level=logging.INFO)
    request = JobRequest.from_json(os.environ["GLAC_REQUEST"])
    spark = _session(request.catalog)
    try:
        return run_maintenance(request, spark.sql)
    finally:
        spark.stop()


if __name__ == "__main__":
    sys.exit(main())
