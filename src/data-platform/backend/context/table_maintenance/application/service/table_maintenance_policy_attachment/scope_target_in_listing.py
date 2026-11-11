"""Define the scope_target_in_listing function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.port.outbound.table_maintenance_policy_attachment import (
    PolicyTargetType,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from context.table_maintenance.application.port.outbound.table import TableMetadataRef


def scope_target_in_listing(kind: PolicyTargetType, path: tuple[str, ...], tables: Sequence[TableMetadataRef]) -> bool:
    """Return whether a catalog or namespace target holds a table of its catalog's ``tables``.

    The table-reading gateway cannot list catalogs or namespaces, so an empty one reads as a
    missing one; a namespace holds a table in it or in a child namespace.
    """
    if kind == PolicyTargetType.CATALOG:
        return bool(tables)
    namespace = ".".join(path[1:])
    return any(t.namespace == namespace or t.namespace.startswith(f"{namespace}.") for t in tables)
