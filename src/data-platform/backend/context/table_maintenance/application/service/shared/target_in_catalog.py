"""Define the target_in_catalog function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import PolicyTargetType
from context.table_maintenance.application.domain.model.table import TableId, TableStatus
from context.table_maintenance.application.port.outbound.table import (
    CatalogAccessDeniedError,
    CatalogNotFoundError,
    TableMetadataRef,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.shared import PolicyTarget
    from context.table_maintenance.application.port.outbound.table import ReadTableMetadataGateway, TablesRepo


def target_in_catalog(target: PolicyTarget, gateway: ReadTableMetadataGateway, tables_repo: TablesRepo) -> bool:
    """Return whether the target still exists; an attachment whose target does not is orphaned.

    A catalog or namespace exists when the catalog says so, holding tables or not. A table is in
    the catalog when table maintenance knows it and it is not dropped, or when it loads under its
    attached path with the same uuid. A catalog the platform's credential cannot read is not known
    to be gone, so its targets count as existing; the refusal shows where the catalog is scanned.
    """
    try:
        if target.type == PolicyTargetType.TABLE:
            return _table_in_catalog(target, gateway, tables_repo)
        if target.type == PolicyTargetType.CATALOG:
            return gateway.catalog_exists(target.path[0])
        return gateway.namespace_exists(target.path[0], ".".join(target.path[1:]))
    except CatalogNotFoundError:
        return False
    except CatalogAccessDeniedError:
        return True


def _table_in_catalog(target: PolicyTarget, gateway: ReadTableMetadataGateway, tables_repo: TablesRepo) -> bool:
    """A table is in the catalog under its attached path, or under any name table maintenance knows it by."""
    table_uuid = target.table_uuid
    known = None if table_uuid is None else tables_repo.get(TableId(table_uuid))
    if known is not None and known.status != TableStatus.DROPPED:
        return True
    path = target.path
    loaded = gateway.load_table(TableMetadataRef(catalog=path[0], namespace=".".join(path[1:-1]), table=path[-1]))
    return loaded is not None and loaded.table_uuid == table_uuid
