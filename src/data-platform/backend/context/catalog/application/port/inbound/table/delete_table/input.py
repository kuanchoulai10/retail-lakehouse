"""Define the DeleteTableUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeleteTableUseCaseInput:
    """Name the table to drop."""

    catalog: str
    namespace: list[str]
    name: str
