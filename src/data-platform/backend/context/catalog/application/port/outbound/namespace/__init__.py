"""Outbound ports for the namespace group."""

from __future__ import annotations

from context.catalog.application.domain.model.catalog import CatalogId
from context.catalog.application.domain.model.namespace import Namespace, NamespaceId
from context.catalog.application.port.outbound.namespace.namespaces_repo import NamespacesRepo

__all__ = [
    "CatalogId",
    "Namespace",
    "NamespaceId",
    "NamespacesRepo",
]
