"""Define the CreateNamespaceUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CreateNamespaceUseCaseOutput:
    """Describe the namespace."""

    catalog: str
    namespace: list[str]
    properties: dict[str, str]
