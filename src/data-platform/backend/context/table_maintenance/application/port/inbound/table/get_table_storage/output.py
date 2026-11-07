"""Define the GetTableStorageUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetTableStorageUseCaseOutput:
    """Describe what a table stores and what maintenance reclaimed lately."""

    current_bytes: int
    current_files: int
    old_snapshot_bytes: int
    old_snapshot_files: int
    window_days: int
    reclaimed: dict[str, int]
    attempts_without_metrics: int
