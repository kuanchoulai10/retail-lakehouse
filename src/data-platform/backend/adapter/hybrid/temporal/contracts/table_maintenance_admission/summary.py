"""Define the table_maintenance_admission_summary helper."""

from __future__ import annotations


def table_maintenance_admission_summary(limit: int) -> str:
    """Return the static summary of the admission workflow, naming its limit."""
    return f"global Spark maintenance admission (limit={limit})"
