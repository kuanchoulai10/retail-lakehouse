"""Define the GetGenericTableUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetGenericTableUseCaseInput:
    """Name the generic table by catalog, namespace parts and name."""

    catalog: str
    namespace: list[str]
    name: str
