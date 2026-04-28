"""Define the ListSnapshotsUseCaseInput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListSnapshotsUseCaseInput:
    """Input for the ListSnapshots use case."""

    namespace: str
    table: str
