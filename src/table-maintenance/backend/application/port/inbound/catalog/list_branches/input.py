"""Define the ListBranchesUseCaseInput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListBranchesUseCaseInput:
    """Input for the ListBranches use case."""

    namespace: str
    table: str
