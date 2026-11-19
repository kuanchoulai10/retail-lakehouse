"""Define the compaction_round_details helper."""

from __future__ import annotations


def compaction_round_details(round_id: str, picked: int, tables: int) -> str:
    """Return the round's id and what it granted, for the workflow's current details.

    The id comes first, so a round the console shows can be found in the Temporal UI.
    """
    partitions = "partition" if picked == 1 else "partitions"
    of_tables = "table" if tables == 1 else "tables"
    return f"round {round_id} · granted {picked} {partitions} of {tables} {of_tables}"
