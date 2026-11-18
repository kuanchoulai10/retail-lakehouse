"""Define the GetNamespaceUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class GetNamespaceUseCaseOutput(UseCaseOutput):
    """Describe the namespace."""

    catalog: str
    namespace: tuple[str, ...]
    properties: dict[str, str]
