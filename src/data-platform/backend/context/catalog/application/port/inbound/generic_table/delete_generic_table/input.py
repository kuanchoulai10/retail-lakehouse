"""Define the DeleteGenericTableUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class DeleteGenericTableUseCaseInput(UseCaseInput):
    """Name the generic table by catalog, namespace parts and name."""

    catalog: str
    namespace: tuple[str, ...]
    name: str
