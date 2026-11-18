"""Define the ListCompactionCandidatesUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class ListCompactionCandidatesUseCaseInput(UseCaseInput):
    """Carry the request: list the compaction candidates of a table."""

    table_uuid: str
