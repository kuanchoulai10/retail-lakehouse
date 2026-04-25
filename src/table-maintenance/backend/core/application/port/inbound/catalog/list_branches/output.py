"""Define the ListBranchesOutput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListBranchesOutputItem:
    """A single branch in the result."""

    name: str
    snapshot_id: int
    max_snapshot_age_ms: int | None
    max_ref_age_ms: int | None
    min_snapshots_to_keep: int | None


@dataclass(frozen=True)
class ListBranchesOutput:
    """Output for the ListBranches use case."""

    branches: list[ListBranchesOutputItem]
