"""Define the ListNamespacesOutput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListNamespacesOutput:
    """Output for the ListNamespaces use case."""

    namespaces: list[str]
