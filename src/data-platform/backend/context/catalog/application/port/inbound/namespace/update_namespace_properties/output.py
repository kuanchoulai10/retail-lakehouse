"""Define the UpdateNamespacePropertiesUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class UpdateNamespacePropertiesUseCaseOutput(UseCaseOutput):
    """Describe the namespace."""

    catalog: str
    namespace: tuple[str, ...]
    properties: dict[str, str]
