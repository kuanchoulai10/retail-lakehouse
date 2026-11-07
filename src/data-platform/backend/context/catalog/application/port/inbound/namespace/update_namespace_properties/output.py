"""Define the UpdateNamespacePropertiesUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UpdateNamespacePropertiesUseCaseOutput:
    """Describe the namespace."""

    catalog: str
    namespace: list[str]
    properties: dict[str, str]
