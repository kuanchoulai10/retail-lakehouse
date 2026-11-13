"""Define the compaction_round_summary helper."""

from __future__ import annotations


def compaction_round_summary(budget_gb_hours: float) -> str:
    """Return the static summary of a scheduled compaction round: its budget."""
    return f"compaction round · budget {budget_gb_hours:g} GB·h"
