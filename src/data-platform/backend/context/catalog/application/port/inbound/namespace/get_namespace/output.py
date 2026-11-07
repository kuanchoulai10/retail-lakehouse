"""Define the GetNamespaceUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetNamespaceUseCaseOutput:
    """Describe the namespace."""

    catalog: str
    namespace: list[str]
    properties: dict[str, str]
