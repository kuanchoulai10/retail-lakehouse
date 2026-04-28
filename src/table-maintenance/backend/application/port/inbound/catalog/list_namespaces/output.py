"""Define the ListNamespacesUseCaseOutput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListNamespacesUseCaseOutput:
    """Output for the ListNamespaces use case."""

    namespaces: list[str]
