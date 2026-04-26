"""Define the ListBranchesInput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListBranchesInput:
    """Input for the ListBranches use case."""

    namespace: str
    table: str
