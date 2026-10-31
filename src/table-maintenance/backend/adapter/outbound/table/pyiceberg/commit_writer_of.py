"""Classify which writer produced a commit from its snapshot summary."""

from __future__ import annotations


def commit_writer_of(summary: dict[str, str]) -> str:
    """Return ``kafka_connect``, ``spark`` or ``unknown`` for a commit summary."""
    if any(key.startswith("kafka.connect.") for key in summary):
        return "kafka_connect"
    if "spark.app.id" in summary:
        return "spark"
    return "unknown"
