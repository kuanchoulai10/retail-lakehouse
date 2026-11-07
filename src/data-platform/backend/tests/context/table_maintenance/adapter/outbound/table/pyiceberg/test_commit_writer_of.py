"""Test how the writer of a snapshot is identified from its summary."""

from __future__ import annotations

from context.table_maintenance.adapter.outbound.table.pyiceberg import commit_writer_of


def test_writer_kafka_connect() -> None:
    """A summary written by the Kafka Connect sink is identified as kafka_connect."""
    summary = {"kafka.connect.task-id": "0", "spark.app.id": "x"}

    assert commit_writer_of(summary) == "kafka_connect"


def test_writer_spark() -> None:
    """A summary with a Spark application id is identified as spark."""
    assert commit_writer_of({"spark.app.id": "app-1", "operation": "replace"}) == ("spark")


def test_writer_unknown() -> None:
    """A summary with no known writer marker is identified as unknown."""
    assert commit_writer_of({"operation": "append"}) == "unknown"
