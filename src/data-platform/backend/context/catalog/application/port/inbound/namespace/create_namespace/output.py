"""Define the CreateNamespaceUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class CreateNamespaceUseCaseOutput(UseCaseOutput):
    """Describe the namespace."""

    catalog: str
    namespace: tuple[str, ...]
    properties: dict[str, str]
