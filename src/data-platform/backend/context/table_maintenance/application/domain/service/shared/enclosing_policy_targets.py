"""Define the enclosing_policy_targets domain service."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.shared import PolicyTarget, PolicyTargetType


def enclosing_policy_targets(catalog: str, namespace: str | None) -> tuple[PolicyTarget, ...]:
    """Return the namespace targets from ``namespace`` up to the top level, then the catalog.

    The namespace is dot-joined; None starts at the catalog.
    """
    levels = tuple(namespace.split(".")) if namespace else ()
    namespaces = tuple(
        PolicyTarget(type=PolicyTargetType.NAMESPACE, path=(catalog, *levels[:depth]))
        for depth in range(len(levels), 0, -1)
    )
    return (*namespaces, PolicyTarget(type=PolicyTargetType.CATALOG, path=(catalog,)))
