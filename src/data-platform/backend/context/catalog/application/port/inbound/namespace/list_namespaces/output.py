"""Define the ListNamespacesUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListNamespacesUseCaseOutputItem:
    """One namespace of the listing; the listing does not carry properties."""

    catalog: str
    namespace: list[str]


@dataclass(frozen=True)
class ListNamespacesUseCaseOutput:
    """Carry the listing."""

    items: list[ListNamespacesUseCaseOutputItem]
