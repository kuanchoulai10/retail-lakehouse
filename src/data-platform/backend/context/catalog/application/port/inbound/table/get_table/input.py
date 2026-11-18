"""Define the GetTableUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class GetTableUseCaseInput(UseCaseInput):
    """Name the table by catalog, namespace parts and name."""

    catalog: str
    namespace: tuple[str, ...]
    name: str
