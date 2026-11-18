"""Define the RenameTableUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class RenameTableUseCaseOutput(UseCaseOutput):
    """Name the table where it now is."""

    catalog: str
    namespace: tuple[str, ...]
    name: str
