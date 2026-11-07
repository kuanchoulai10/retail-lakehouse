"""Define the RenameTableUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RenameTableUseCaseOutput:
    """Name the table where it now is."""

    catalog: str
    namespace: list[str]
    name: str
