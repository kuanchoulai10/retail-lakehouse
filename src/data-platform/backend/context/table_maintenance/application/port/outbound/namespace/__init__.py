"""Outbound ports for the namespace group."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.namespace import Namespace
from context.table_maintenance.application.domain.model.shared import (
    NamespaceId,
    TableDiscoveryPolicyId,
    TableMaintenancePolicyId,
)
from context.table_maintenance.application.port.outbound.namespace.namespaces_repo import NamespacesRepo

__all__ = [
    "Namespace",
    "NamespaceId",
    "NamespacesRepo",
    "TableDiscoveryPolicyId",
    "TableMaintenancePolicyId",
]
