"""Define the DeleteNamespaceUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class DeleteNamespaceUseCaseInput(UseCaseInput):
    """Name the namespace to delete: its catalog and its parts, outermost first."""

    catalog: str
    namespace: tuple[str, ...]
