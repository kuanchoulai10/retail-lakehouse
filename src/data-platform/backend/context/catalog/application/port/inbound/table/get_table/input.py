"""Define the GetTableUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetTableUseCaseInput:
    """Name the table by catalog, namespace parts and name."""

    catalog: str
    namespace: list[str]
    name: str
