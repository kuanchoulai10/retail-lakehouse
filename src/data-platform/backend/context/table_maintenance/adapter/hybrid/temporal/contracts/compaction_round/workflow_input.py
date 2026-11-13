"""Define the CompactionRoundWorkflowInput workflow contract."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompactionRoundWorkflowInput:
    """Start one compaction round; the round reads its rules from the worker's settings, so it takes no field yet."""
