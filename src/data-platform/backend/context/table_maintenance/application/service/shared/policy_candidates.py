"""Define the policy_candidates function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table import TableId, TableName
from context.table_maintenance.application.domain.service.shared import (
    candidate_policy_targets,
    enclosing_policy_targets,
)
from context.table_maintenance.application.exceptions import NotFoundError, ValidationError
from context.table_maintenance.application.port.outbound.table import CatalogNotFoundError, TableMetadataRef
from context.table_maintenance.application.service.shared.translate_domain_errors import translate_domain_errors

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.shared import PolicyTarget
    from context.table_maintenance.application.port.outbound.table import ReadTableMetadataGateway, TablesRepo


def policy_candidates(
    gateway: ReadTableMetadataGateway,
    tables_repo: TablesRepo,
    *,
    catalog: str | None,
    namespace: str | None,
    table: str | None,
    table_uuid: str | None,
) -> tuple[PolicyTarget, ...]:
    """Return the targets whose attachments may apply to a place, nearest first; every kind of policy walks them.

    A ``table_uuid`` without ``catalog`` names a table table maintenance records, placed by its recorded
    name (NotFoundError without a record). A catalog, or a catalog and a dot-joined namespace, walks from
    that level up without reading the catalog: whether the place exists is the caller's question. A table
    by name takes the ``table_uuid`` given, else its uuid from the catalog (NotFoundError when the catalog
    does not hold it; a refused catalog raises CatalogAccessDeniedError, untouched).
    """
    if catalog is None:
        return _recorded_table_candidates(tables_repo, table_uuid)
    if table is None:
        return enclosing_policy_targets(catalog, namespace)
    if namespace is None:
        raise ValidationError("a table needs its namespace")
    if table_uuid is None:
        try:
            loaded = gateway.load_table(TableMetadataRef(catalog=catalog, namespace=namespace, table=table))
        except CatalogNotFoundError as exc:
            raise NotFoundError(str(exc)) from exc
        if loaded is None:
            raise NotFoundError(f"table {catalog}.{namespace}.{table} not found")
        table_uuid = loaded.table_uuid
    with translate_domain_errors():
        name = TableName(catalog=catalog, namespace=namespace, table=table)
        return candidate_policy_targets(name, table_uuid)


def _recorded_table_candidates(tables_repo: TablesRepo, table_uuid: str | None) -> tuple[PolicyTarget, ...]:
    if table_uuid is None:
        raise ValidationError("name a catalog or a table uuid")
    recorded = tables_repo.get(TableId(table_uuid))
    if recorded is None:
        raise NotFoundError(f"table {table_uuid} not found")
    return candidate_policy_targets(recorded.name, recorded.id.value)
