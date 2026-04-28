"""Define the ListNamespacesUseCaseInput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListNamespacesUseCaseInput:
    """Input for the ListNamespaces use case."""
