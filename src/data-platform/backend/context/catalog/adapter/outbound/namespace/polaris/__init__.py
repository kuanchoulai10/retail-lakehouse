"""Polaris adapters of the namespace aggregate: the namespaces repo."""

from __future__ import annotations

from context.catalog.adapter.outbound.namespace.polaris.namespace_from_polaris import (
    namespace_from_polaris,
)
from context.catalog.adapter.outbound.namespace.polaris.namespaces_polaris_repo import (
    NamespacesPolarisRepo,
)

__all__ = [
    "NamespacesPolarisRepo",
    "namespace_from_polaris",
]
