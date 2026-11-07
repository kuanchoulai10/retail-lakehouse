"""Define the GetNamespaceUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetNamespaceUseCaseInput:
    """Name the namespace to get: its catalog and its parts, outermost first."""

    catalog: str
    namespace: list[str]
