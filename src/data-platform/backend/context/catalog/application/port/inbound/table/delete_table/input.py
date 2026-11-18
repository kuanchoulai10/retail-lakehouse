"""Define the DeleteTableUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class DeleteTableUseCaseInput(UseCaseInput):
    """Name the table to drop."""

    catalog: str
    namespace: tuple[str, ...]
    name: str
