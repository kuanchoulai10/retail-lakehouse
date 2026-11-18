"""Define the GetNamespaceUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class GetNamespaceUseCaseInput(UseCaseInput):
    """Name the namespace to get: its catalog and its parts, outermost first."""

    catalog: str
    namespace: tuple[str, ...]
