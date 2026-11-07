"""Define the DeleteNamespaceUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeleteNamespaceUseCaseInput:
    """Name the namespace to delete: its catalog and its parts, outermost first."""

    catalog: str
    namespace: list[str]
