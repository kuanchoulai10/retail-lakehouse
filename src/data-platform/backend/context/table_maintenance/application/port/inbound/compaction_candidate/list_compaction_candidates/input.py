"""Define the ListCompactionCandidatesUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListCompactionCandidatesUseCaseInput:
    """Carry the request: list the compaction candidates of a table."""

    table_uuid: str
