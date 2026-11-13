"""Define the compaction_round_details helper."""

from __future__ import annotations


def compaction_round_details(picked: int, tables: int) -> str:
    """Return what a compaction round granted, for the workflow's current details."""
    partitions = "partition" if picked == 1 else "partitions"
    of_tables = "table" if tables == 1 else "tables"
    return f"granted {picked} {partitions} of {tables} {of_tables}"
