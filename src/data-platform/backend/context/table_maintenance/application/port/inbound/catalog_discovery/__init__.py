"""Inbound ports for the catalog_discovery group.

A catalog's discovery has no use case of its own: syncing the discovered
tables records it, and the table listing reads it, both through
``CatalogDiscoveriesRepo``.
"""

from __future__ import annotations

__all__ = []
