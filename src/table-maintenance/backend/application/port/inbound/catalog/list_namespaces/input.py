"""Define the ListNamespacesInput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListNamespacesInput:
    """Input for the ListNamespaces use case."""
