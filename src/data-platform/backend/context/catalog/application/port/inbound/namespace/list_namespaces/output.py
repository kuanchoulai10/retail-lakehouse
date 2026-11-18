"""Define the ListNamespacesUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class ListNamespacesUseCaseOutput(UseCaseOutput):
    """Carry the listing."""

    class Namespace(UseCaseOutput):
        """One namespace of the listing; the listing does not carry properties."""

        catalog: str
        namespace: tuple[str, ...]

    items: tuple[Namespace, ...]
