"""Define the DeleteGenericTableUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeleteGenericTableUseCaseInput:
    """Name the generic table by catalog, namespace parts and name."""

    catalog: str
    namespace: list[str]
    name: str
